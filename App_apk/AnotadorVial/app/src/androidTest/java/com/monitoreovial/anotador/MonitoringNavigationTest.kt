package com.monitoreovial.anotador

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class MonitoringNavigationTest {
    @get:Rule val compose = createAndroidComposeRule<MainActivity>()

    @Test fun navigationOpensRealSectionsWithoutStartingCapture() {
        compose.onNodeWithTag("tab_1").performClick()
        compose.onNodeWithText("Recorridos guardados").assertIsDisplayed()
        compose.onNodeWithTag("tab_2").performClick()
        compose.onNodeWithText("Eventos registrados").assertIsDisplayed()
        compose.onNodeWithTag("tab_3").performClick()
        compose.onNodeWithText("Preferencias").assertIsDisplayed()
        compose.onNodeWithText("Tema oscuro").assertIsDisplayed()
        compose.onNodeWithTag("tab_0").performClick()
        compose.onNodeWithTag("home_content").assertIsDisplayed()
    }
}
