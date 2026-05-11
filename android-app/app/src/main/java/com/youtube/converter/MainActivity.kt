package com.youtube.converter

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.fragment.app.Fragment
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.youtube.converter.databinding.ActivityMainBinding
import com.youtube.converter.ui.ConverterFragment
import com.youtube.converter.ui.HistoryFragment
import com.youtube.converter.ui.SearchFragment

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        PythonManager.init(this)

        val bottomNav = binding.bottomNavigation
        bottomNav.setOnItemSelectedListener { item ->
            when (item.itemId) {
                R.id.nav_converter -> showFragment(ConverterFragment())
                R.id.nav_search -> showFragment(SearchFragment())
                R.id.nav_history -> showFragment(HistoryFragment())
            }
            true
        }

        if (savedInstanceState == null) {
            val sharedUrl = intent?.getStringExtra(Intent.EXTRA_TEXT)
            val converterFragment = ConverterFragment()
            if (sharedUrl != null) {
                val args = Bundle()
                args.putString("shared_url", sharedUrl)
                converterFragment.arguments = args
            }
            showFragment(converterFragment)
            bottomNav.selectedItemId = R.id.nav_converter
        }
    }

    private fun showFragment(fragment: Fragment) {
        supportFragmentManager.beginTransaction()
            .replace(R.id.fragment_container, fragment)
            .commit()
    }
}
