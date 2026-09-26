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

  // 2. AndroidManifest fixes:
  // - Remove 'assetsPaths' from MainActivity configChanges (fails AAPT linking on SDK 35)
  // - Enable showWhenLocked and turnScreenOn so incoming calls wake screen & show on lock screen
  // - Register BOOT_COMPLETED receiver so softphone wakes up automatically on phone start
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
        if (activity.$ && activity.$['android:name'] === '.MainActivity') {
          activity.$['android:showWhenLocked'] = 'true';
          activity.$['android:turnScreenOn'] = 'true';
          activity.$['android:showForAllUsers'] = 'true';
        }
      }
    }

    if (mainApplication) {
      // 1. Ensure service stopsWithTask="false" so OS keeps it alive after swipe-to-kill
      if (!mainApplication.service) {
        mainApplication.service = [];
      }
      const notifService = mainApplication.service.find(
        (s) => s.$?.['android:name'] === 'expo.modules.notifications.service.NotificationsService'
      );
      if (notifService) {
        notifService.$['android:stopWithTask'] = 'false';
      } else {
        mainApplication.service.push({
          $: {
            'android:name': 'expo.modules.notifications.service.NotificationsService',
            'android:exported': 'false',
            'android:stopWithTask': 'false',
          },
        });
      }

      // 2. Broadcast receivers for boot, power on, and package update wake-ups
      if (!mainApplication.receiver) {
        mainApplication.receiver = [];
      }
      const hasBootReceiver = mainApplication.receiver.some(
        (r) => r.$?.['android:name'] === 'expo.modules.notifications.service.NotificationsService'
      );
      if (!hasBootReceiver) {
        mainApplication.receiver.push({
          $: {
            'android:name': 'expo.modules.notifications.service.NotificationsService',
            'android:exported': 'true',
          },
          'intent-filter': [
            {
              action: [
                { $: { 'android:name': 'android.intent.action.BOOT_COMPLETED' } },
                { $: { 'android:name': 'android.intent.action.QUICKBOOT_POWERON' } },
                { $: { 'android:name': 'com.htc.intent.action.QUICKBOOT_POWERON' } },
                { $: { 'android:name': 'android.intent.action.MY_PACKAGE_REPLACED' } },
                { $: { 'android:name': 'android.intent.action.ACTION_POWER_CONNECTED' } },
              ],
            },
          ],
        });
      }
    }

    return config;
  });

  return config;
};

module.exports = withAndroidResolutionStrategy;
