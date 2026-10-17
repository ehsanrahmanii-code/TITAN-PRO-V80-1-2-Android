plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.chaquo.python")
}

android {
    namespace = "com.titan.v80"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.titan.v80"
        minSdk = 24
        targetSdk = 34
        versionCode = 813
        versionName = "80.1.2-nervous"

        ndk {
            // CI: arm64 only (phones). Emulator x86_64 can be added later.
            abiFilters += listOf("arm64-v8a")
        }

        python {
            version = "3.11"
            pip {
                // Keep deps minimal but enough for TITAN engine
                install("numpy==1.26.4")
                install("pandas==2.1.4")
                install("flask==3.0.3")
                install("waitress==3.0.0")
                install("requests==2.32.3")
            }
        }
    }

    buildTypes {
        release { isMinifyEnabled = false }
        debug { applicationIdSuffix = ".debug" }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }

    packaging {
        resources {
            excludes += setOf("META-INF/LICENSE*", "META-INF/NOTICE*")
        }
        jniLibs {
            useLegacyPackaging = true
        }
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("androidx.webkit:webkit:1.11.0")
}
