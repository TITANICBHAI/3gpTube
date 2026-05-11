package com.youtube.converter

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.security.MessageDigest

data class ConversionStatus(
    val fileId: String,
    val status: String,
    val progress: String,
    val outputPath: String?,
    val videoTitle: String?,
    val fileSize: Long,
)

data class SearchResult(
    val id: String,
    val title: String,
    val url: String,
    val duration: String,
    val channel: String,
    val thumbnail: String,
)

class ConverterViewModel : ViewModel() {

    private val _conversionStatus = MutableLiveData<ConversionStatus?>()
    val conversionStatus: LiveData<ConversionStatus?> = _conversionStatus

    private val _searchResults = MutableLiveData<List<SearchResult>>()
    val searchResults: LiveData<List<SearchResult>> = _searchResults

    private val _searchLoading = MutableLiveData(false)
    val searchLoading: LiveData<Boolean> = _searchLoading

    private val _searchError = MutableLiveData<String?>()
    val searchError: LiveData<String?> = _searchError

    private var currentFileId: String? = null
    private var pollingActive = false

    fun startConversion(url: String, format: String, quality: String) {
        val fileId = generateFileId(url)
        currentFileId = fileId

        viewModelScope.launch(Dispatchers.IO) {
            try {
                val converter = PythonManager.getConverter()
                converter.callAttr("start_conversion", url, fileId, format, quality)
                startPolling(fileId)
            } catch (e: Exception) {
                _conversionStatus.postValue(
                    ConversionStatus(fileId, "failed", "Error: ${e.message}", null, null, 0)
                )
            }
        }
    }

    private fun startPolling(fileId: String) {
        pollingActive = true
        viewModelScope.launch(Dispatchers.IO) {
            while (pollingActive) {
                try {
                    val converter = PythonManager.getConverter()
                    val statusMap = converter.callAttr("get_status", fileId).asMap()

                    val status = statusMap["status"]?.toString() ?: "unknown"
                    val progress = statusMap["progress"]?.toString() ?: ""
                    val outputPath = statusMap["output_path"]?.toString()
                    val videoTitle = statusMap["video_title"]?.toString()
                    val fileSize = statusMap["file_size"]?.toLong() ?: 0L

                    _conversionStatus.postValue(
                        ConversionStatus(fileId, status, progress, outputPath, videoTitle, fileSize)
                    )

                    if (status == "completed" || status == "failed") {
                        pollingActive = false
                        break
                    }
                } catch (e: Exception) {
                    // keep polling
                }
                delay(1500)
            }
        }
    }

    fun searchYouTube(query: String) {
        _searchLoading.value = true
        _searchError.value = null
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val converter = PythonManager.getConverter()
                val raw = converter.callAttr("search_youtube", query)
                val results = mutableListOf<SearchResult>()
                for (item in raw.asList()) {
                    val m = item.asMap()
                    results.add(
                        SearchResult(
                            id = m["id"]?.toString() ?: "",
                            title = m["title"]?.toString() ?: "Unknown",
                            url = m["url"]?.toString() ?: "",
                            duration = m["duration"]?.toString() ?: "",
                            channel = m["channel"]?.toString() ?: "",
                            thumbnail = m["thumbnail"]?.toString() ?: "",
                        )
                    )
                }
                _searchResults.postValue(results)
                _searchLoading.postValue(false)
            } catch (e: Exception) {
                _searchError.postValue("Search failed: ${e.message}")
                _searchLoading.postValue(false)
            }
        }
    }

    fun resetStatus() {
        pollingActive = false
        _conversionStatus.value = null
    }

    private fun generateFileId(url: String): String {
        val input = "$url${System.currentTimeMillis()}"
        val bytes = MessageDigest.getInstance("MD5").digest(input.toByteArray())
        return bytes.take(8).joinToString("") { "%02x".format(it) }
    }
}
