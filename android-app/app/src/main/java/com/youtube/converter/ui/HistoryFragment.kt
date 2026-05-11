package com.youtube.converter.ui

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.core.content.FileProvider
import androidx.fragment.app.Fragment
import androidx.recyclerview.widget.LinearLayoutManager
import com.youtube.converter.PythonManager
import com.youtube.converter.databinding.FragmentHistoryBinding
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

data class HistoryItem(
    val fileId: String,
    val title: String,
    val format: String,
    val filePath: String,
    val fileSize: Long,
)

class HistoryFragment : Fragment() {

    private var _binding: FragmentHistoryBinding? = null
    private val binding get() = _binding!!

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentHistoryBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        binding.recyclerView.layoutManager = LinearLayoutManager(requireContext())
        loadHistory()
    }

    private fun loadHistory() {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val converter = PythonManager.getConverter()
                val all = converter.callAttr("get_all_status").asMap()
                val items = mutableListOf<HistoryItem>()
                for ((fileId, statusObj) in all) {
                    val status = statusObj.asMap()
                    if (status["status"]?.toString() != "completed") continue
                    val path = status["output_path"]?.toString() ?: continue
                    val file = File(path)
                    if (!file.exists()) continue
                    items.add(
                        HistoryItem(
                            fileId = fileId.toString(),
                            title = status["video_title"]?.toString() ?: "Unknown",
                            format = if (path.endsWith(".mp3")) "MP3" else "MP4",
                            filePath = path,
                            fileSize = file.length(),
                        )
                    )
                }
                withContext(Dispatchers.Main) {
                    if (items.isEmpty()) {
                        binding.emptyText.visibility = View.VISIBLE
                        binding.recyclerView.visibility = View.GONE
                    } else {
                        binding.emptyText.visibility = View.GONE
                        binding.recyclerView.visibility = View.VISIBLE
                        binding.recyclerView.adapter = HistoryAdapter(items) { item ->
                            openFile(item.filePath)
                        }
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.emptyText.text = "Error loading history"
                    binding.emptyText.visibility = View.VISIBLE
                }
            }
        }
    }

    private fun openFile(path: String) {
        val file = File(path)
        if (!file.exists()) return
        val uri: Uri = FileProvider.getUriForFile(requireContext(), "${requireContext().packageName}.fileprovider", file)
        val mime = if (path.endsWith(".mp3")) "audio/mpeg" else "video/mp4"
        val intent = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, mime)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        startActivity(Intent.createChooser(intent, "Open with"))
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
