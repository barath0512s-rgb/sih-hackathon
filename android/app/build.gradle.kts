import groovy.json.JsonSlurper

plugins {
    id("com.android.application")
}

// The launcher label is config.APP_NAME (tools/android/sync_config.py writes app_config.json).
@Suppress("UNCHECKED_CAST")
val appName = (JsonSlurper().parse(file("src/main/assets/app_config.json")) as Map<String, Any>)["app_name"] as String

// The web page and its fonts come from the repo root, so the hub and the
// tablet always serve the same frontend.html.
val webAssets = layout.buildDirectory.dir("generated/webassets")
val copyWebAssets = tasks.register<Copy>("copyWebAssets") {
    from(rootProject.projectDir.resolve("../frontend.html"))
    from(rootProject.projectDir.resolve("../static")) { into("static") }
    into(webAssets.map { it.dir("web") })
}

android {
    namespace = "org.team8bitpool.app"
    compileSdk = 36

    defaultConfig {
        applicationId = "org.team8bitpool.app"
        minSdk = 28
        targetSdk = 36
        versionCode = 1
        versionName = "0.1-m1"
        testInstrumentationRunner = "android.test.InstrumentationTestRunner"
        resValue("string", "app_name", appName)
        // The Realme Pad Mini (arm64) and the x86_64 emulator; keeps the APK smaller.
        ndk { abiFilters += setOf("arm64-v8a", "x86_64") }
    }

    sourceSets["main"].assets.directories.add(webAssets.get().asFile.path)
    buildFeatures { resValues = true }

    buildTypes {
        release {
            isMinifyEnabled = false
            // Signed with the debug key for now: a release key is a team decision (M5).
            signingConfig = signingConfigs.getByName("debug")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    testOptions {
        unitTests.isReturnDefaultValues = true
    }
    packaging {
        resources.excludes += setOf("META-INF/LICENSE*", "META-INF/NOTICE*")
    }
}

tasks.named("preBuild") { dependsOn(copyWebAssets) }

dependencies {
    implementation("org.nanohttpd:nanohttpd:2.3.1")          // BSD-3-Clause
    // sherpa-onnx 1.13.8 (Apache-2.0), the official release AAR; not in git (50 MB):
    // python tools/android/fetch_sherpa_aar.py downloads it and checks its SHA-256.
    implementation(files("libs/sherpa-onnx-1.13.8.aar"))
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20240303")           // android.jar's org.json is a stub in unit tests
}
