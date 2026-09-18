package com.pulsefinanceiro.dreai

import android.os.Bundle
import androidx.activity.enableEdgeToEdge
import androidx.core.view.WindowCompat
import com.facebook.react.ReactActivity
import com.facebook.react.ReactActivityDelegate
import com.facebook.react.defaults.DefaultNewArchitectureEntryPoint.fabricEnabled
import com.facebook.react.defaults.DefaultReactActivityDelegate

class MainActivity : ReactActivity() {

  override fun onCreate(savedInstanceState: Bundle?) {
    // Em Android 15+ o edge-to-edge passa a valer de qualquer jeito quando o
    // app mira API 35+. Declarar aqui torna o comportamento igual em todas as
    // versões, em vez de mudar sozinho conforme o aparelho.
    enableEdgeToEdge()
    // O JS é quem posiciona: o React Native recebe os insets e as telas
    // aplicam com useSafeAreaInsets. Nada de altura chutada em XML.
    WindowCompat.setDecorFitsSystemWindows(window, false)
    super.onCreate(null)
  }

  override fun getMainComponentName(): String = "KansasIAFinanceira"

  override fun createReactActivityDelegate(): ReactActivityDelegate =
    DefaultReactActivityDelegate(this, mainComponentName, fabricEnabled)
}
