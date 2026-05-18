package com.youtube.converter

import android.annotation.SuppressLint
import android.content.Intent
import android.graphics.Bitmap
import android.os.Bundle
import android.view.KeyEvent
import android.view.View
import android.webkit.CookieManager
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.FrameLayout
import android.widget.ProgressBar
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var progressBar: ProgressBar
    private var serverStarted = false

    // YouTube login overlay
    private var loginOverlay: FrameLayout? = null
    private var loginWebView: WebView? = null

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.web_view)
        progressBar = findViewById(R.id.progress_bar)

        setupWebView()
        startFlaskServer()
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView() {
        val settings: WebSettings = webView.settings
        settings.javaScriptEnabled = true
        settings.domStorageEnabled = true
        settings.allowFileAccess = true
        settings.allowContentAccess = true
        settings.setSupportZoom(true)
        settings.builtInZoomControls = true
        settings.displayZoomControls = false
        settings.useWideViewPort = true
        settings.loadWithOverviewMode = true
        settings.cacheMode = WebSettings.LOAD_NO_CACHE

        webView.webViewClient = object : WebViewClient() {
            override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                progressBar.visibility = View.VISIBLE
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                progressBar.visibility = View.GONE
            }

            override fun shouldOverrideUrlLoading(
                view: WebView?,
                request: WebResourceRequest?
            ): Boolean {
                val url = request?.url?.toString() ?: return false

                return when {
                    // intercept cookie-login → open YouTube WebView overlay
                    url.contains("127.0.0.1:5000/cookie-login") ||
                    url.contains("localhost:5000/cookie-login") -> {
                        openYouTubeLoginOverlay()
                        true
                    }
                    // keep local Flask traffic inside this WebView
                    url.startsWith("http://127.0.0.1") ||
                    url.startsWith("http://localhost") -> false
                    // block everything else
                    else -> true
                }
            }

            override fun onReceivedError(
                view: WebView?,
                errorCode: Int,
                description: String?,
                failingUrl: String?
            ) {
                if (failingUrl?.contains("127.0.0.1:5000") == true && !serverStarted) {
                    CoroutineScope(Dispatchers.Main).launch {
                        delay(1500)
                        view?.reload()
                    }
                }
            }
        }

        webView.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView?, newProgress: Int) {
                progressBar.progress = newProgress
                if (newProgress == 100) progressBar.visibility = View.GONE
            }
        }
    }

    private fun startFlaskServer() {
        progressBar.visibility = View.VISIBLE
        webView.loadData(
            "<html><body style='background:#1a1a2e;color:#eee;font-family:Arial,sans-serif;" +
            "display:flex;align-items:center;justify-content:center;height:100vh;margin:0'>" +
            "<div style='text-align:center'><h2 style='color:#4a90a4'>3gpTube</h2>" +
            "<p>Starting local server...</p></div></body></html>",
            "text/html", "utf-8"
        )

        CoroutineScope(Dispatchers.IO).launch {
            if (!Python.isStarted()) {
                Python.start(AndroidPlatform(applicationContext))
            }
            Python.getInstance().getModule("flask_server").callAttr("start")
            waitForServer()

            val sharedUrl = intent?.getStringExtra(Intent.EXTRA_TEXT)
            val loadUrl = if (!sharedUrl.isNullOrBlank()) {
                "http://127.0.0.1:5000/?url=${android.net.Uri.encode(sharedUrl)}"
            } else {
                "http://127.0.0.1:5000/"
            }

            withContext(Dispatchers.Main) {
                serverStarted = true
                webView.loadUrl(loadUrl)
            }
        }
    }

    private suspend fun waitForServer(maxAttempts: Int = 30) {
        repeat(maxAttempts) {
            try {
                val conn = URL("http://127.0.0.1:5000/ping").openConnection() as HttpURLConnection
                conn.connectTimeout = 1000
                conn.readTimeout = 1000
                if (conn.responseCode == 200) {
                    conn.disconnect()
                    return
                }
                conn.disconnect()
            } catch (e: Exception) {
                // not ready yet
            }
            delay(1000)
        }
    }

    // ── YouTube login overlay ─────────────────────────────────────────────────

    @SuppressLint("SetJavaScriptEnabled")
    private fun openYouTubeLoginOverlay() {
        if (loginOverlay != null) return

        val root = findViewById<FrameLayout>(R.id.root_layout)

        val overlay = FrameLayout(this)
        overlay.setBackgroundColor(0xFF000000.toInt())
        overlay.layoutParams = FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.MATCH_PARENT,
            FrameLayout.LayoutParams.MATCH_PARENT
        )

        // Top bar
        val bar = android.widget.LinearLayout(this)
        bar.orientation = android.widget.LinearLayout.HORIZONTAL
        bar.setBackgroundColor(0xFF333333.toInt())
        bar.setPadding(16, 16, 16, 16)
        val barParams = FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.MATCH_PARENT,
            android.widget.LinearLayout.LayoutParams.WRAP_CONTENT
        )
        barParams.gravity = android.view.Gravity.TOP

        val titleTv = TextView(this)
        titleTv.text = "Log in to YouTube — then tap Save Cookies"
        titleTv.setTextColor(0xFFFFFFFF.toInt())
        titleTv.textSize = 13f
        titleTv.layoutParams = android.widget.LinearLayout.LayoutParams(0, android.widget.LinearLayout.LayoutParams.WRAP_CONTENT, 1f)

        val saveBtn = Button(this)
        saveBtn.text = "Save Cookies"
        saveBtn.setBackgroundColor(0xFF4a904a.toInt())
        saveBtn.setTextColor(0xFFFFFFFF.toInt())
        saveBtn.layoutParams = android.widget.LinearLayout.LayoutParams(
            android.widget.LinearLayout.LayoutParams.WRAP_CONTENT,
            android.widget.LinearLayout.LayoutParams.WRAP_CONTENT
        )

        val cancelBtn = Button(this)
        cancelBtn.text = "Cancel"
        cancelBtn.setBackgroundColor(0xFF555555.toInt())
        cancelBtn.setTextColor(0xFFFFFFFF.toInt())
        cancelBtn.layoutParams = android.widget.LinearLayout.LayoutParams(
            android.widget.LinearLayout.LayoutParams.WRAP_CONTENT,
            android.widget.LinearLayout.LayoutParams.WRAP_CONTENT
        ).also { it.marginStart = 8 }

        bar.addView(titleTv)
        bar.addView(saveBtn)
        bar.addView(cancelBtn)

        // YouTube WebView
        val ytWebView = WebView(this)
        val ytSettings = ytWebView.settings
        ytSettings.javaScriptEnabled = true
        ytSettings.domStorageEnabled = true
        ytSettings.userAgentString = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        val webParams = FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.MATCH_PARENT,
            FrameLayout.LayoutParams.MATCH_PARENT
        )
        webParams.topMargin = 120 // leave room for bar
        ytWebView.layoutParams = webParams

        CookieManager.getInstance().setAcceptCookie(true)
        CookieManager.getInstance().setAcceptThirdPartyCookies(ytWebView, true)

        ytWebView.loadUrl("https://accounts.google.com/ServiceLogin?service=youtube&hl=en")

        saveBtn.setOnClickListener {
            extractAndSaveCookies(ytWebView)
        }

        cancelBtn.setOnClickListener {
            closeLoginOverlay()
        }

        overlay.addView(ytWebView)
        overlay.addView(bar, barParams)
        root.addView(overlay)

        loginOverlay = overlay
        loginWebView = ytWebView
    }

    private fun extractAndSaveCookies(ytWebView: WebView) {
        val cm = CookieManager.getInstance()
        val domains = listOf(
            ".youtube.com",
            "youtube.com",
            ".google.com",
            "google.com",
            ".accounts.google.com",
            "accounts.google.com",
            ".ggpht.com",
            ".ytimg.com",
        )

        val cookieMap = mutableMapOf<String, String>()
        for (domain in domains) {
            val cookies = cm.getCookie(domain)
            if (!cookies.isNullOrBlank()) {
                cookieMap[domain] = cookies
            }
        }

        if (cookieMap.isEmpty()) {
            runOnUiThread {
                val tv = TextView(this)
                tv.text = "No cookies found yet — please log in first."
                tv.setTextColor(0xFFFFFF00.toInt())
                tv.setPadding(16, 8, 16, 8)
                (loginOverlay as FrameLayout).addView(tv,
                    FrameLayout.LayoutParams(
                        FrameLayout.LayoutParams.MATCH_PARENT,
                        FrameLayout.LayoutParams.WRAP_CONTENT
                    ).also { it.gravity = android.view.Gravity.BOTTOM })
            }
            return
        }

        CoroutineScope(Dispatchers.IO).launch {
            try {
                val json = JSONObject()
                val cookiesJson = JSONObject()
                for ((domain, value) in cookieMap) {
                    cookiesJson.put(domain, value)
                }
                json.put("cookies", cookiesJson)

                val conn = URL("http://127.0.0.1:5000/save-cookies").openConnection() as HttpURLConnection
                conn.requestMethod = "POST"
                conn.setRequestProperty("Content-Type", "application/json")
                conn.doOutput = true
                conn.connectTimeout = 5000
                conn.readTimeout = 5000

                OutputStreamWriter(conn.outputStream).use { it.write(json.toString()) }
                val responseCode = conn.responseCode
                conn.disconnect()

                withContext(Dispatchers.Main) {
                    if (responseCode == 200) {
                        closeLoginOverlay()
                        webView.loadUrl("http://127.0.0.1:5000/cookies?success=1")
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    val tv = TextView(this@MainActivity)
                    tv.text = "Save failed: ${e.message}"
                    tv.setTextColor(0xFFFF4444.toInt())
                    tv.setPadding(16, 8, 16, 8)
                }
            }
        }
    }

    private fun closeLoginOverlay() {
        loginOverlay?.let {
            (it.parent as? FrameLayout)?.removeView(it)
        }
        loginOverlay = null
        loginWebView?.destroy()
        loginWebView = null
    }

    // ── navigation ────────────────────────────────────────────────────────────

    override fun onKeyDown(keyCode: Int, event: KeyEvent?): Boolean {
        if (keyCode == KeyEvent.KEYCODE_BACK) {
            if (loginOverlay != null) {
                closeLoginOverlay()
                return true
            }
            if (webView.canGoBack()) {
                webView.goBack()
                return true
            }
        }
        return super.onKeyDown(keyCode, event)
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        val sharedUrl = intent?.getStringExtra(Intent.EXTRA_TEXT)
        if (!sharedUrl.isNullOrBlank() && serverStarted) {
            webView.loadUrl("http://127.0.0.1:5000/?url=${android.net.Uri.encode(sharedUrl)}")
        }
    }
}
