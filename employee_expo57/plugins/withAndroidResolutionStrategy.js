const { withProjectBuildGradle, withAndroidManifest } = require('@expo/config-plugins');

const withAndroidResolutionStrategy = (config) => {
  // 1. Gradle resolution strategy: force stable androidx.core 1.15.0 (minCompileSdk=35)
  config = withProjectBuildGradle(config, (config) => {
    if (config.modResults.language === 'groovy') {
      const gradleBlock = `
allprojects {
    configurations.all {
        resolutionStrategy {
            force 'androidx.core:core:1.15.0'
            force 'androidx.core:core-ktx:1.15.0'
        }
    }
}
`;
      if (!config.modResults.contents.includes('androidx.core:core:1.15.0')) {
        config.modResults.contents += gradleBlock;
      }
    }
    return config;
  });

  // 2. AndroidManifest fix: Remove 'assetsPaths' from MainActivity configChanges
  // 'assetsPaths' is an Android 16 (API 36) flag that fails AAPT resource linking on SDK 35
  config = withAndroidManifest(config, (config) => {
    const mainApplication = config.modResults.manifest.application?.[0];
    if (mainApplication?.activity) {
      for (const activity of mainApplication.activity) {
        if (activity.$ && activity.$['android:configChanges']) {
          activity.$['android:configChanges'] = activity.$['android:configChanges']
            .replace('|assetsPaths', '')
            .replace('assetsPaths|', '')
            .replace('assetsPaths', '');
        }
      }
    }
    return config;
  });

  return config;
};

module.exports = withAndroidResolutionStrategy;
