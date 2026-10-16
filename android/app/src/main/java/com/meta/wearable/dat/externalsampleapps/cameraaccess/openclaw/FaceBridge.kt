package com.meta.wearable.dat.externalsampleapps.cameraaccess.openclaw

import android.util.Base64
import android.util.Log
import com.meta.wearable.dat.externalsampleapps.cameraaccess.gemini.GeminiConfig
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject

/** Calls the aiGlass backend people endpoints (saved people only). Reuses the same host/token as OpenClawBridge. */
class FaceBridge {
    companion object { private const val TAG = "FaceBridge" }

    private val client = OkHttpClient.Builder()
        .readTimeout(60, TimeUnit.SECONDS)
        .connectTimeout(10, TimeUnit.SECONDS)
        .build()

    private fun baseUrl() = "${GeminiConfig.openClawHost}:${GeminiConfig.openClawPort}"

    private fun post(path: String, body: JSONObject): JSONObject? {
        val request = Request.Builder()
            .url(baseUrl() + path)
            .post(body.toString().toRequestBody("application/json".toMediaType()))
            .addHeader("Authorization", "Bearer ${GeminiConfig.openClawGatewayToken}")
            .addHeader("Content-Type", "application/json")
            .build()
        client.newCall(request).execute().use { resp ->
            val text = resp.body?.string() ?: return null
            if (resp.code !in 200..299) {
                Log.d(TAG, "HTTP ${resp.code}: ${text.take(200)}")
                return null
            }
            return JSONObject(text)
        }
    }

    suspend fun recognize(jpeg: ByteArray?): ToolResult = withContext(Dispatchers.IO) {
        if (jpeg == null) return@withContext ToolResult.Failure("No camera frame available yet.")
        try {
            val b64 = Base64.encodeToString(jpeg, Base64.NO_WRAP)
            val json = post("/face/recognize", JSONObject().put("image_b64", b64))
                ?: return@withContext ToolResult.Failure("Face service unreachable.")
            if (json.optBoolean("recognized")) {
                val name = json.optString("name")
                val notes = json.optString("notes")
                val lastTalked = json.optJSONArray("recent")?.optString(0).orEmpty()
                val profile = json.optJSONObject("public_profile")?.optString("summary").orEmpty()
                val msg = buildString {
                    append("This is $name.")
                    if (notes.isNotBlank()) append(" $notes.")
                    if (lastTalked.isNotBlank()) append(" Last time: $lastTalked")
                    if (profile.isNotBlank()) append(" Profile: $profile")
                }
                ToolResult.Success(msg)
            } else {
                ToolResult.Success("I don't recognize this person — they're not in your saved people.")
            }
        } catch (e: Exception) {
            ToolResult.Failure("Face recognition error: ${e.message}")
        }
    }

    suspend fun enroll(jpeg: ByteArray?, name: String, notes: String = "", profile: String = ""): ToolResult =
        withContext(Dispatchers.IO) {
            if (jpeg == null) return@withContext ToolResult.Failure("No camera frame available yet.")
            if (name.isBlank()) return@withContext ToolResult.Failure("I need a name to save this person.")
            try {
                val b64 = Base64.encodeToString(jpeg, Base64.NO_WRAP)
                val json = post(
                    "/face/enroll",
                    JSONObject().put("name", name).put("notes", notes)
                        .put("profile_link", profile).put("image_b64", b64),
                ) ?: return@withContext ToolResult.Failure("Face service unreachable.")
                if (json.optBoolean("ok")) {
                    ToolResult.Success("Saved $name. I'll recognize them next time.")
                } else {
                    ToolResult.Failure(json.optString("error", "Could not save the face."))
                }
            } catch (e: Exception) {
                ToolResult.Failure("Enrollment error: ${e.message}")
            }
        }
}
