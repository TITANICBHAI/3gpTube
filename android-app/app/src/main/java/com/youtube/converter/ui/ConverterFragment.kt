package com.youtube.converter.ui

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import androidx.core.content.FileProvider
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import com.google.android.material.snackbar.Snackbar
import com.youtube.converter.ConverterViewModel
import com.youtube.converter.R
import com.youtube.converter.databinding.FragmentConverterBinding
import java.io.File

class ConverterFragment : Fragment() {

    private var _binding: FragmentConverterBinding? = null
    private val binding get() = _binding!!
    private val viewModel: ConverterViewModel by activityViewModels()

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentConverterBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        arguments?.getString("shared_url")?.let {
            binding.urlInput.setText(it)
        }

        setupFormatSpinner()
        setupQualitySpinner()
        setupObservers()

        binding.formatSpinner.setOnItemSelectedListener(object : android.widget.AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: android.widget.AdapterView<*>?, view: View?, pos: Int, id: Long) {
                updateQualitySpinner(pos == 0)
            }
            override fun onNothingSelected(parent: android.widget.AdapterView<*>?) {}
        })

        binding.convertButton.setOnClickListener {
            val url = binding.urlInput.text.toString().trim()
            if (url.isEmpty()) {
                Snackbar.make(view, "Please enter a YouTube URL", Snackbar.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            val finalUrl = if (url.startsWith("http")) url else "https://$url"
            val isVideo = binding.formatSpinner.selectedItemPosition == 0
            val format = if (isVideo) "mp4" else "mp3"
            val quality = getSelectedQuality(isVideo)
            viewModel.resetStatus()
            viewModel.startConversion(finalUrl, format, quality)
            binding.progressGroup.visibility = View.VISIBLE
            binding.downloadButton.visibility = View.GONE
            binding.convertButton.isEnabled = false
        }

        binding.downloadButton.setOnClickListener {
            val path = binding.downloadButton.tag as? String ?: return@setOnClickListener
            openFile(path)
        }
    }

    private fun setupFormatSpinner() {
        val formats = arrayOf("MP4 Video", "MP3 Audio")
        val adapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_dropdown_item, formats)
        binding.formatSpinner.adapter = adapter
    }

    private fun setupQualitySpinner() {
        updateQualitySpinner(true)
    }

    private fun updateQualitySpinner(isVideo: Boolean) {
        val items = if (isVideo) {
            arrayOf("360p (Small) ~25MB/5min", "480p (Medium) ~40MB/5min", "720p HD ~90MB/5min", "1080p Full HD ~180MB/5min")
        } else {
            arrayOf("128 kbps (Good) ~5MB/5min", "192 kbps (High) ~7MB/5min", "256 kbps (Very High) ~9MB/5min", "320 kbps (Max) ~12MB/5min")
        }
        val adapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_dropdown_item, items)
        binding.qualitySpinner.adapter = adapter
        if (isVideo) binding.qualitySpinner.setSelection(1)
    }

    private fun getSelectedQuality(isVideo: Boolean): String {
        val pos = binding.qualitySpinner.selectedItemPosition
        return if (isVideo) {
            listOf("360p", "480p", "720p", "1080p")[pos]
        } else {
            listOf("128k", "192k", "256k", "320k")[pos]
        }
    }

    private fun setupObservers() {
        viewModel.conversionStatus.observe(viewLifecycleOwner) { status ->
            status ?: return@observe
            binding.statusText.text = status.progress
            when (status.status) {
                "downloading" -> {
                    binding.progressBar.isIndeterminate = true
                    binding.progressLabel.text = "Downloading..."
                }
                "converting" -> {
                    binding.progressBar.isIndeterminate = true
                    binding.progressLabel.text = "Converting..."
                }
                "completed" -> {
                    binding.progressBar.isIndeterminate = false
                    binding.progressBar.progress = 100
                    binding.progressLabel.text = "Done!"
                    binding.convertButton.isEnabled = true
                    val path = status.outputPath
                    if (path != null) {
                        val sizeStr = formatSize(status.fileSize)
                        binding.downloadButton.text = "Open / Share (${status.videoTitle ?: "file"}) [$sizeStr]"
                        binding.downloadButton.tag = path
                        binding.downloadButton.visibility = View.VISIBLE
                    }
                }
                "failed" -> {
                    binding.progressBar.isIndeterminate = false
                    binding.progressLabel.text = "Failed"
                    binding.convertButton.isEnabled = true
                    Snackbar.make(binding.root, status.progress, Snackbar.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun openFile(path: String) {
        val file = File(path)
        if (!file.exists()) {
            Snackbar.make(binding.root, "File not found", Snackbar.LENGTH_SHORT).show()
            return
        }
        val uri: Uri = FileProvider.getUriForFile(requireContext(), "${requireContext().packageName}.fileprovider", file)
        val mime = if (path.endsWith(".mp3")) "audio/mpeg" else "video/mp4"
        val intent = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, mime)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        val shareIntent = Intent.createChooser(intent, "Open with")
        startActivity(shareIntent)
    }

    private fun formatSize(bytes: Long): String {
        if (bytes <= 0) return "?"
        val mb = bytes / (1024.0 * 1024.0)
        return if (mb >= 1) "%.1f MB".format(mb) else "%.0f KB".format(bytes / 1024.0)
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
