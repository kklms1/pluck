import { cpSync, mkdirSync } from "fs";
const src = "node_modules/pretendard/dist/web/static/woff2";
const dst = "public/fonts";
mkdirSync(dst, { recursive: true });
for (const w of ["Regular","Medium","SemiBold","Bold","ExtraBold","Black"]) {
  cpSync(`${src}/Pretendard-${w}.woff2`, `${dst}/Pretendard-${w}.woff2`);
}
console.log("Pretendard fonts copied to public/fonts");
