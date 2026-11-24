plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
    id("com.google.devtools.ksp")
}
android {
    namespace = "nl.jarvis.mobile"
    compileSdk { version = release(37) { minorApiLevel = 2 } }
    defaultConfig {
        applicationId = "nl.jarvis.mobile"
        minSdk = 26
        targetSdk = 36
        versionCode = 705
        versionName = "0.7.5"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        buildConfigField("String", "FIREBASE_APP_ID", "\"${providers.gradleProperty("firebaseAppId").getOrElse("")}\"")
        buildConfigField("String", "FIREBASE_PROJECT_ID", "\"${providers.gradleProperty("firebaseProjectId").getOrElse("")}\"")
        buildConfigField("String", "FIREBASE_API_KEY", "\"${providers.gradleProperty("firebaseApiKey").getOrElse("")}\"")
        buildConfigField("String", "FIREBASE_SENDER_ID", "\"${providers.gradleProperty("firebaseSenderId").getOrElse("")}\"")
        if (providers.gradleProperty("firebaseAppId").isPresent) {
            resValue("string", "google_app_id", providers.gradleProperty("firebaseAppId").get())
            resValue("string", "google_api_key", providers.gradleProperty("firebaseApiKey").getOrElse(""))
            resValue("string", "project_id", providers.gradleProperty("firebaseProjectId").getOrElse(""))
            resValue("string", "gcm_defaultSenderId", providers.gradleProperty("firebaseSenderId").getOrElse(""))
        }
    }
    buildFeatures { compose = true; buildConfig = true }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    buildTypes {
        release { isMinifyEnabled = false } // unsigned; owner controls release signing
    }
    testOptions { unitTests.isReturnDefaultValues = true }
    packaging { resources.excludes += setOf("META-INF/AL2.0", "META-INF/LGPL2.1") }
}
dependencies {
    implementation(platform("androidx.compose:compose-bom:2026.09.00"))
    implementation("androidx.activity:activity-compose:1.13.0")
    implementation("androidx.fragment:fragment:1.9.1")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui-tooling-preview")
    debugImplementation("androidx.compose.ui:ui-tooling")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.11.1")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.11.1")
    implementation("androidx.lifecycle:lifecycle-process:2.11.1")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.11.0")
    implementation("androidx.datastore:datastore-preferences:1.3.0")
    implementation("androidx.room:room-runtime:2.8.5")
    implementation("androidx.room:room-ktx:2.8.5")
    ksp("androidx.room:room-compiler:2.8.5")
    implementation("com.squareup.okhttp3:okhttp:5.5.1")
    implementation("androidx.work:work-runtime-ktx:2.12.0")
    implementation(platform("com.google.firebase:firebase-bom:35.2.0"))
    implementation("com.google.firebase:firebase-messaging")
    testImplementation("junit:junit:4.13.2")
    testImplementation("com.squareup.okhttp3:mockwebserver3:5.5.1")
    androidTestImplementation("androidx.test.ext:junit:1.3.0")
    androidTestImplementation("androidx.test:runner:1.7.0")
    androidTestImplementation(platform("androidx.compose:compose-bom:2026.09.00"))
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    androidTestImplementation("com.squareup.okhttp3:mockwebserver3:5.5.1")
    androidTestImplementation("com.squareup.okhttp3:okhttp-tls:5.5.1")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}
