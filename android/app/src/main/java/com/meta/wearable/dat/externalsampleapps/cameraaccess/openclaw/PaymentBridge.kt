package com.meta.wearable.dat.externalsampleapps.cameraaccess.openclaw

import android.content.Context
import android.content.Intent
import android.graphics.BitmapFactory
import android.net.Uri
import android.util.Log
import com.google.mlkit.vision.barcode.BarcodeScannerOptions
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import kotlin.coroutines.resume
import kotlinx.coroutines.suspendCancellableCoroutine

/**
 * UPI QR payments through the glasses camera.
 *
 * Flow: scanQr() decodes a UPI QR from the latest glasses frame and remembers the payee;
 * initiate() then launches the phone's UPI app pre-filled via a upi://pay intent.
 * The user always authorizes the payment in the UPI app itself (tap / fingerprint / PIN) —
 * this bridge never holds credentials and never completes a payment on its own.
 */
class PaymentBridge(private val context: Context) {
    companion object {
        private const val TAG = "PaymentBridge"
        // Deliberately low: a voice pipeline can mishear an amount, so cap what a single
        // spoken command can ever prepare. Larger payments are done manually.
        private const val MAX_AMOUNT_INR = 1_400.0
    }

    private val scanner = BarcodeScanning.getClient(
        BarcodeScannerOptions.Builder()
            .setBarcodeFormats(Barcode.FORMAT_QR_CODE)
            .build()
    )

    /** The last scanned UPI URI, pending an amount + confirmation. */
    @Volatile
    private var pendingUpiUri: Uri? = null

    suspend fun scanQr(jpeg: ByteArray?): ToolResult {
        if (jpeg == null) {
            return ToolResult.Failure("No camera frame available. The camera stream must be running to scan a QR code.")
        }
        val bitmap = BitmapFactory.decodeByteArray(jpeg, 0, jpeg.size)
            ?: return ToolResult.Failure("Could not decode the camera frame.")

        val rawValues: List<String> = suspendCancellableCoroutine { cont ->
            scanner.process(InputImage.fromBitmap(bitmap, 0))
                .addOnSuccessListener { barcodes ->
                    cont.resume(barcodes.mapNotNull { it.rawValue })
                }
                .addOnFailureListener { e ->
                    Log.e(TAG, "QR scan failed", e)
                    cont.resume(emptyList())
                }
        }

        if (rawValues.isEmpty()) {
            return ToolResult.Failure("No QR code visible. Ask the user to look directly at the QR code and hold still for a moment.")
        }

        val upiRaw = rawValues.firstOrNull { it.startsWith("upi://", ignoreCase = true) }
            ?: return ToolResult.Failure("Found a QR code but it is not a UPI payment code.")

        val uri = Uri.parse(upiRaw)
        val payeeVpa = uri.getQueryParameter("pa")
        if (payeeVpa.isNullOrBlank()) {
            return ToolResult.Failure("The UPI QR code is malformed (no payee address).")
        }
        val payeeName = uri.getQueryParameter("pn") ?: payeeVpa
        val embeddedAmount = uri.getQueryParameter("am")

        pendingUpiUri = uri
        Log.d(TAG, "Scanned UPI QR: payee=$payeeName vpa=$payeeVpa amount=${embeddedAmount ?: "none"}")
        Log.d(TAG, "QR params=${uri.queryParameterNames} rawQR=$upiRaw")

        val amountInfo = if (embeddedAmount.isNullOrBlank()) {
            "The QR does not fix an amount; ask the user how much to pay."
        } else {
            "The QR fixes the amount at INR $embeddedAmount."
        }
        return ToolResult.Success(
            "UPI payment QR scanned. Payee: \"$payeeName\" (UPI ID: $payeeVpa). $amountInfo " +
                "Confirm payee and amount aloud with the user before initiating the payment."
        )
    }

    fun initiate(amountArg: String): ToolResult {
        val uri = pendingUpiUri
            ?: return ToolResult.Failure("No scanned QR pending. Scan the payment QR first.")

        val embeddedAmount = uri.getQueryParameter("am")
        val amount: Double? = when {
            !embeddedAmount.isNullOrBlank() -> embeddedAmount.toDoubleOrNull()
            else -> amountArg.replace(",", "").trim().toDoubleOrNull()
        }
        if (amount == null || amount <= 0.0) {
            return ToolResult.Failure("Invalid amount \"$amountArg\". Ask the user for a clear amount in rupees.")
        }
        if (amount > MAX_AMOUNT_INR) {
            return ToolResult.Failure(
                "Amount INR $amount is above the voice payment limit of INR ${MAX_AMOUNT_INR.toInt()}. " +
                    "Tell the user this is too large to pay by voice and they should pay it manually in their UPI app."
            )
        }

        // Preserve the original QR parameters (merchant codes, signatures); only add the
        // amount + currency when the QR left them open. A unique transaction reference is
        // added when absent — without it some PSPs decline repeat payments as duplicates.
        val builder = uri.buildUpon()
        if (embeddedAmount.isNullOrBlank()) {
            builder.appendQueryParameter("am", String.format("%.2f", amount))
            if (uri.getQueryParameter("cu").isNullOrBlank()) builder.appendQueryParameter("cu", "INR")
        }
        if (uri.getQueryParameter("tr").isNullOrBlank()) {
            builder.appendQueryParameter("tr", "VC${System.currentTimeMillis()}")
        }
        val finalUri = builder.build()
        Log.d(TAG, "Final UPI URI: $finalUri")

        return try {
            val payIntent = Intent(Intent.ACTION_VIEW, finalUri)
            val chooser = Intent.createChooser(payIntent, "Pay via").apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(chooser)
            pendingUpiUri = null
            Log.d(TAG, "Launched UPI intent for INR $amount")
            ToolResult.Success(
                "The UPI app has been opened on the phone, pre-filled with INR ${String.format("%.2f", amount)} " +
                    "to ${uri.getQueryParameter("pn") ?: uri.getQueryParameter("pa")}. " +
                    "Tell the user to check their phone and approve the payment there."
            )
        } catch (e: Exception) {
            Log.e(TAG, "Failed to launch UPI intent", e)
            ToolResult.Failure("Could not open a UPI app on the phone: ${e.message}")
        }
    }

    fun clearPending() {
        pendingUpiUri = null
    }
}
