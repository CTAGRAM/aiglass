package com.meta.wearable.dat.externalsampleapps.cameraaccess.gemini

/** Holds the most recent camera JPEG so on-demand tools (QR pay) can grab the current view. */
object LatestFrame {
    @Volatile
    var jpeg: ByteArray? = null
}
