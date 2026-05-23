// ===============================================
// 全国都市比較対応版（卒研レベル完成版）
// OSM施設データ取得 → CSV保存
// Node.js 18+
// ===============================================

import fs from "fs";
import { wards } from "./wards.js";

// ------------------------------------
// API設定
// ------------------------------------
const API =
  "https://lz4.overpass-api.de/api/interpreter";

// ------------------------------------
// sleep
// ------------------------------------
function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

// ------------------------------------
// 共通取得関数（3回再試行）
// ------------------------------------
// =====================================
// 取得できるまで無限再接続版 fetchCount
// =====================================

async function fetchCount(
  cityName,
  wardName,
  queryPart
) {
  const query = `
[out:json][timeout:90];
area["name"="${cityName}"]["boundary"="administrative"]->.city;
area["name"="${wardName}"]["boundary"="administrative"](area.city)->.a;
(
 node${queryPart}(area.a);
 way${queryPart}(area.a);
 relation${queryPart}(area.a);
);
out count;
`;

  let retry = 1;

  while (true) {
    try {
      console.log(
        `${cityName} ${wardName} 接続 ${retry}回目`
      );

      const res = await fetch(API, {
        method: "POST",
        headers: {
          "Content-Type": "text/plain",
          "Accept": "application/json",
          "User-Agent": "urban-analysis-app"
        },
        body: query
      });

      const text = await res.text();

      // JSONなら成功
      if (text.trim().startsWith("{")) {

        const data = JSON.parse(text);

        const count = Number(
          data.elements?.[0]?.tags?.total || 0
        );

        console.log(
          `${cityName} ${wardName} 成功 (${count}件)`
        );

        return count;
      }

      console.log(
        `${cityName} ${wardName} 応答失敗`
      );

    } catch (err) {
      console.log(
        `${cityName} ${wardName} 通信失敗`
      );
    }

    retry++;

    // 15秒待って再接続
    await new Promise((r) =>
      setTimeout(r, 15000)
    );
  }
}

// ------------------------------------
// メイン処理
// ------------------------------------
async function run() {
  const results = [];

  for (const ward of wards) {

    console.log(
      `取得中: ${ward.city} ${ward.name}`
    );

    const convenience =
      await fetchCount(
        ward.city,
        ward.name,
        '["shop"="convenience"]'
      );

    const supermarket =
      await fetchCount(
        ward.city,
        ward.name,
        '["shop"="supermarket"]'
      );

    const drugstore =
      await fetchCount(
        ward.city,
        ward.name,
        '["shop"="chemist"]'
      );

    const hospital =
      await fetchCount(
        ward.city,
        ward.name,
        '["amenity"="hospital"]'
      );

    const station =
      await fetchCount(
        ward.city,
        ward.name,
        '["railway"="station"]'
      );

    const park =
      await fetchCount(
        ward.city,
        ward.name,
        '["leisure"="park"]'
      );

    results.push({
      city: ward.city,
      ward: ward.name,
      convenience,
      supermarket,
      drugstore,
      station,
      park
    });

    console.log(
      `${ward.city} ${ward.name} 完了`
    );

    // 負荷対策
    await sleep(8000);
  }

  // ------------------------------------
  // CSV生成
  // ------------------------------------
  let csv =
"都市,区名,コンビニ数,スーパー数,ドラッグストア数,駅数,公園数\n";

  results.forEach((r) => {
    csv +=
`${r.city},${r.ward},${r.convenience ?? ""},${r.supermarket ?? ""},${r.drugstore ?? ""},${r.hospital ?? ""},${r.station ?? ""},${r.park ?? ""}\n`;
  });

  fs.writeFileSync(
    "urban_analysis.csv",
    csv,
    "utf-8"
  );

  console.log("CSV出力完了");
  console.log("urban_analysis.csv");
}

run();