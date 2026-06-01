import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.setConcurrency(2);
// 고화질 인코딩
Config.setCodec("h264");
Config.setCrf(18);
