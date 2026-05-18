package com.youtube.converter

import android.annotation.SuppressLint
import android.content.Intent
import android.graphics.Bitmap
import android.os.Bundle
import android.view.KeyEvent
import android.view.View
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.ProgressBar
import androidx.appcompat.app.AppCompatActivity
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var progressBar: ProgressBar
    private var serverStarted = false

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

            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                val url = request?.url?.toString() ?: return false
                return if (url.startsWith("http://127.0.0.1") || url.startsWith("http://localhost")) {
                    false
                } else {
                    true
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
            "<html><body style='background:#1a1a2e;color:#eee;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;'>" +
            "<div style='text-align:center'><h2>3gpTube</h2><p>Starting server...</p></div></body></html>",
            "text/html", "utf-8"
        )

        CoroutineScope(Dispatchers.IO).launch {
            if (!Python.isStarted()) {
                Python.start(AndroidPlatform(applicationContext))
            }

            val py = Python.getInstance()
            py.getModule("flask_server").callAttr("start")

            waitForServer()

            val sharedUrl = intent?.getStringExtra(Intent.EXTRA_TEXT)
            val loadUrl = if (!sharedUrl.isNullOrBlank()) {
                val encoded = android.net.Uri.encode(sharedUrl)
                "http://127.0.0.1:5000/?url=$encoded"
            } else {
                "http://127.0.0.1:5000/"
            }

            kotlinx.coroutines.withContext(Dispatchers.Main) {
                serverStarted = true
                webView.loadUrl(loadUrl)
            }
        }
    }

    private suspend fun waitForServer(maxAttempts: Int = 30) {
        repeat(maxAttempts) {
            try {
                val conn = java.net.URL("http://127.0.0.1:5000/ping").openConnection() as java.net.HttpURLConnection
                conn.connectTimeout = 1000
                conn.readTimeout = 1000
                if (conn.responseCode == 200) {
                    return
                }
                conn.disconnect()
            } catch (e: Exception) {
                // not ready yet
            }
            delay(1000)
        }
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent?): Boolean {
        if (keyCode == KeyEvent.KEYCODE_BACK && webView.canGoBack()) {
            webView.goBack()
            return true
        }
        return super.onKeyDown(keyCode, event)
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        val sharedUrl = intent?.getStringExtra(Intent.EXTRA_TEXT)
        if (!sharedUrl.isNullOrBlank() && serverStarted) {
            val encoded = android.net.Uri.encode(sharedUrl)
            webView.loadUrl("http://127.0.0.1:5000/?url=$encoded")
        }
    }
}
