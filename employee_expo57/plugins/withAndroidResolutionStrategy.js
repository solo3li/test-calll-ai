const { withProjectBuildGradle } = require('@expo/config-plugins');

const withAndroidResolutionStrategy = (config) => {
  return withProjectBuildGradle(config, (config) => {
    if (config.modResults.language === 'groovy') {
      const gradleBlock = `
allprojects {
    configurations.all {
        resolutionStrategy {
            force 'androidx.core:core:1.15.0'
            force 'androidx.core:core-ktx:1.15.0'
        }
    }
    afterEvaluate { project ->
        project.tasks.matching { it.name.contains("AarMetadata") }.configureEach {
            enabled = false
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
};

module.exports = withAndroidResolutionStrategy;
