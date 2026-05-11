package com.youtube.converter.ui

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.EditorInfo
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.recyclerview.widget.LinearLayoutManager
import com.youtube.converter.ConverterViewModel
import com.youtube.converter.SearchResult
import com.youtube.converter.databinding.FragmentSearchBinding

class SearchFragment : Fragment() {

    private var _binding: FragmentSearchBinding? = null
    private val binding get() = _binding!!
    private val viewModel: ConverterViewModel by activityViewModels()
    private lateinit var adapter: SearchResultAdapter

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentSearchBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        adapter = SearchResultAdapter { result ->
            navigateToConverter(result)
        }
        binding.recyclerView.layoutManager = LinearLayoutManager(requireContext())
        binding.recyclerView.adapter = adapter

        binding.searchButton.setOnClickListener { doSearch() }
        binding.searchInput.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_SEARCH) { doSearch(); true } else false
        }

        viewModel.searchResults.observe(viewLifecycleOwner) { results ->
            adapter.submitList(results)
            binding.emptyText.visibility = if (results.isEmpty()) View.VISIBLE else View.GONE
        }
        viewModel.searchLoading.observe(viewLifecycleOwner) { loading ->
            binding.progressBar.visibility = if (loading) View.VISIBLE else View.GONE
        }
        viewModel.searchError.observe(viewLifecycleOwner) { error ->
            if (error != null) binding.emptyText.text = error
        }
    }

    private fun doSearch() {
        val q = binding.searchInput.text.toString().trim()
        if (q.isNotEmpty()) viewModel.searchYouTube(q)
    }

    private fun navigateToConverter(result: SearchResult) {
        val converterFragment = ConverterFragment().apply {
            arguments = Bundle().apply { putString("shared_url", result.url) }
        }
        parentFragmentManager.beginTransaction()
            .replace(com.youtube.converter.R.id.fragment_container, converterFragment)
            .addToBackStack(null)
            .commit()
        requireActivity().findViewById<com.google.android.material.bottomnavigation.BottomNavigationView>(
            com.youtube.converter.R.id.bottom_navigation
        ).selectedItemId = com.youtube.converter.R.id.nav_converter
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
