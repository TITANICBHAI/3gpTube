package com.youtube.converter.ui

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.youtube.converter.databinding.ItemHistoryBinding

class HistoryAdapter(
    private val items: List<HistoryItem>,
    private val onOpen: (HistoryItem) -> Unit
) : RecyclerView.Adapter<HistoryAdapter.ViewHolder>() {

    inner class ViewHolder(private val binding: ItemHistoryBinding) : RecyclerView.ViewHolder(binding.root) {
        fun bind(item: HistoryItem) {
            binding.titleText.text = item.title
            val sizeStr = formatSize(item.fileSize)
            binding.infoText.text = "${item.format} • $sizeStr"
            binding.openButton.setOnClickListener { onOpen(item) }
        }

        private fun formatSize(bytes: Long): String {
            val mb = bytes / (1024.0 * 1024.0)
            return if (mb >= 1) "%.1f MB".format(mb) else "%.0f KB".format(bytes / 1024.0)
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemHistoryBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) = holder.bind(items[position])
    override fun getItemCount() = items.size
}
