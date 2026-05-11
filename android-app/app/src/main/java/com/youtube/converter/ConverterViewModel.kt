package com.youtube.converter

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.chaquo.python.PyObject
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

fun Map<PyObject, PyObject>.str(key: String): String? =
    entries.find { it.key.toString() == key }?.value?.toString()

fun Map<PyObject, PyObject>.long(key: String): Long =
    str(key)?.toLongOrNull() ?: 0L

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

                    val status = statusMap.str("status") ?: "unknown"
                    val progress = statusMap.str("progress") ?: ""
                    val outputPath = statusMap.str("output_path")
                    val videoTitle = statusMap.str("video_title")
                    val fileSize = statusMap.long("file_size")

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
                            id = m.str("id") ?: "",
                            title = m.str("title") ?: "Unknown",
                            url = m.str("url") ?: "",
                            duration = m.str("duration") ?: "",
                            channel = m.str("channel") ?: "",
                            thumbnail = m.str("thumbnail") ?: "",
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
