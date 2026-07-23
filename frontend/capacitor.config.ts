import type { CapacitorConfig } from '@capacitor/cli';

const isAndroidDebug =
  process.env['FAN_ANDROID_DEBUG'] === '1';

const config: CapacitorConfig = {
  appId: 'com.strupsts.fan',
  appName: 'F.A.N.',
  webDir: 'www',

  ...(isAndroidDebug
    ? {
        server: {
          androidScheme: 'http',
          cleartext: true,
        },
      }
    : {}),
};

export default config;
