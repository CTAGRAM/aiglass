package com.meta.wearable.dat.externalsampleapps.cameraaccess.gemini

import android.annotation.SuppressLint
import android.content.Context
import android.media.AudioAttributes
import android.media.AudioDeviceInfo
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.AudioTrack
import android.media.MediaRecorder
import android.os.Build
import android.util.Log
import java.io.ByteArrayOutputStream
import android.media.AudioManager as AndroidAudioManager

class AudioManager {
    companion object {
        private const val TAG = "AudioManager"
        private const val MIN_SEND_BYTES = 3200 // 100ms at 16kHz mono Int16 = 1600 frames * 2 bytes
    }

    var onAudioCaptured: ((ByteArray) -> Unit)? = null

    private var audioRecord: AudioRecord? = null
    private var audioTrack: AudioTrack? = null
    private var captureThread: Thread? = null
    @Volatile
    private var isCapturing = false
    private val accumulatedData = ByteArrayOutputStream()
    private val accumulateLock = Any()

    private var systemAudioManager: AndroidAudioManager? = null
    private var routedToBtDevice = false

    @SuppressLint("MissingPermission")
    fun startCapture(context: Context) {
        if (isCapturing) return

        // Prefer the glasses' Bluetooth mic/speaker (open-ear headset) so the phone can stay pocketed.
        Log.d(TAG, "Mic routing -> ${routeToGlassesHeadsetIfAvailable(context)}")

        val bufferSize = AudioRecord.getMinBufferSize(
            GeminiConfig.INPUT_AUDIO_SAMPLE_RATE,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT
        )

        audioRecord = AudioRecord(
            MediaRecorder.AudioSource.VOICE_COMMUNICATION,
            GeminiConfig.INPUT_AUDIO_SAMPLE_RATE,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
            bufferSize
        )

        audioTrack = AudioTrack.Builder()
            .setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_VOICE_COMMUNICATION)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build()
            )
            .setAudioFormat(
                AudioFormat.Builder()
                    .setSampleRate(GeminiConfig.OUTPUT_AUDIO_SAMPLE_RATE)
                    .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                    .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                    .build()
            )
            .setTransferMode(AudioTrack.MODE_STREAM)
            .setBufferSizeInBytes(
                AudioTrack.getMinBufferSize(
                    GeminiConfig.OUTPUT_AUDIO_SAMPLE_RATE,
                    AudioFormat.CHANNEL_OUT_MONO,
                    AudioFormat.ENCODING_PCM_16BIT
                ) * 2
            )
            .build()

        audioRecord?.startRecording()
        audioTrack?.play()
        isCapturing = true

        audioRecord?.routedDevice?.let {
            Log.d(TAG, "AudioRecord live on device: ${it.productName} (type=${it.type})")
        }

        synchronized(accumulateLock) {
            accumulatedData.reset()
        }

        captureThread = Thread({
            val buffer = ByteArray(bufferSize)
            var tapCount = 0
            while (isCapturing) {
                val read = audioRecord?.read(buffer, 0, buffer.size) ?: break
                if (read > 0) {
                    tapCount++
                    synchronized(accumulateLock) {
                        accumulatedData.write(buffer, 0, read)
                        if (accumulatedData.size() >= MIN_SEND_BYTES) {
                            val chunk = accumulatedData.toByteArray()
                            accumulatedData.reset()
                            if (tapCount <= 3) {
                                Log.d(TAG, "Sending chunk: ${chunk.size} bytes (~${chunk.size / 32}ms)")
                            }
                            onAudioCaptured?.invoke(chunk)
                        }
                    }
                }
            }
        }, "audio-capture").also { it.start() }

        Log.d(TAG, "Audio capture started (16kHz mono PCM16)")
    }

    /**
     * Routes voice capture + playback to the glasses' Bluetooth headset (open-ear mic/speaker) when
     * they're connected as an HFP/LE-Audio device, so the phone can stay in the user's pocket.
     * Falls back silently to the phone mic when no headset is available. Returns a human-readable
     * description of the chosen device (for logging).
     */
    private fun routeToGlassesHeadsetIfAvailable(context: Context): String {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) {
            return "phone mic (Android < 12, no communication-device routing)"
        }
        val am = context.getSystemService(Context.AUDIO_SERVICE) as AndroidAudioManager
        systemAudioManager = am
        am.mode = AndroidAudioManager.MODE_IN_COMMUNICATION

        val headset = am.availableCommunicationDevices.firstOrNull {
            it.type == AudioDeviceInfo.TYPE_BLUETOOTH_SCO || it.type == AudioDeviceInfo.TYPE_BLE_HEADSET
        } ?: return "phone mic (no Bluetooth headset among communication devices)"

        routedToBtDevice = am.setCommunicationDevice(headset)
        return if (routedToBtDevice) {
            "glasses/BT headset: ${headset.productName} (type=${headset.type})"
        } else {
            "phone mic (setCommunicationDevice rejected ${headset.productName})"
        }
    }

    private fun clearHeadsetRouting() {
        val am = systemAudioManager ?: return
        if (routedToBtDevice && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            am.clearCommunicationDevice()
        }
        am.mode = AndroidAudioManager.MODE_NORMAL
        systemAudioManager = null
        routedToBtDevice = false
    }

    fun playAudio(data: ByteArray) {
        if (!isCapturing || data.isEmpty()) return
        audioTrack?.write(data, 0, data.size)
    }

    fun stopPlayback() {
        audioTrack?.pause()
        audioTrack?.flush()
        audioTrack?.play()
    }

    fun stopCapture() {
        if (!isCapturing) return
        isCapturing = false

        captureThread?.join(1000)
        captureThread = null

        // Flush remaining accumulated audio
        synchronized(accumulateLock) {
            if (accumulatedData.size() > 0) {
                val chunk = accumulatedData.toByteArray()
                accumulatedData.reset()
                onAudioCaptured?.invoke(chunk)
            }
        }

        audioRecord?.stop()
        audioRecord?.release()
        audioRecord = null

        audioTrack?.stop()
        audioTrack?.release()
        audioTrack = null

        clearHeadsetRouting()

        Log.d(TAG, "Audio capture stopped")
    }
}
