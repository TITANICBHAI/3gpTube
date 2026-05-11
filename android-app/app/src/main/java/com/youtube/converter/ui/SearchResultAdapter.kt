package com.youtube.converter.ui

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.youtube.converter.SearchResult
import com.youtube.converter.databinding.ItemSearchResultBinding

class SearchResultAdapter(
    private val onItemClick: (SearchResult) -> Unit
) : ListAdapter<SearchResult, SearchResultAdapter.ViewHolder>(DIFF_CALLBACK) {

    inner class ViewHolder(private val binding: ItemSearchResultBinding) : RecyclerView.ViewHolder(binding.root) {
        fun bind(result: SearchResult) {
            binding.titleText.text = result.title
            binding.channelText.text = result.channel
            binding.durationText.text = result.duration
            binding.root.setOnClickListener { onItemClick(result) }
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemSearchResultBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    companion object {
        val DIFF_CALLBACK = object : DiffUtil.ItemCallback<SearchResult>() {
            override fun areItemsTheSame(a: SearchResult, b: SearchResult) = a.id == b.id
            override fun areContentsTheSame(a: SearchResult, b: SearchResult) = a == b
        }
    }
}
