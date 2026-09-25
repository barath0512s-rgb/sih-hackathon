package org.team8bitpool.app.bridge

import android.webkit.JavascriptInterface
import org.json.JSONObject

/**
 * Content-pack import for the page (Settings → Content pack):
 *  - pickFile(): the system file picker, which covers USB drives, SD cards and Downloads;
 *  - fromHub(url): download from the hub over HTTPS (the hub's own CA, installed by
 *    the teacher as for the browser, is trusted; see res/xml/network_security_config.xml).
 * The result arrives as window.onPackImported({ok, message, counts}).
 */
class PackBridge(private val onPick: () -> Unit, private val onDownload: (String) -> Unit,
                 private val currentStatus: () -> JSONObject) {
    @JavascriptInterface fun pickFile() = onPick()
    @JavascriptInterface fun fromHub(url: String) = onDownload(url)
    @JavascriptInterface fun status(): String = currentStatus().toString()
}
