import math
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import statsmodels.api as sm

from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

# ============================================
# 日本語フォント
# ============================================
plt.rcParams["font.family"] = "Meiryo"
plt.rcParams["axes.unicode_minus"] = False

# ============================================
# ファイル設定
# ============================================
CSV_FILE = "city.csv"
GEOJSON_FILE = "tokyo.geojson"

TARGET_COL = "平均地価"

OUT_DIR = Path("analysis_output")
OUT_DIR.mkdir(exist_ok=True)

# ============================================
# CSV読み込み
# ============================================
df = pd.read_csv(CSV_FILE, encoding="utf-8")

df.columns = [
    "都市",
    "区名",
    "平均地価",
    "コンビニ数",
    "スーパー数",
    "ドラッグストア数",
    "病院数",
    "駅数",
    "公園数",
    "学校数",
]

# ============================================
# 数値変換
# ============================================
numeric_cols = [
    "平均地価",
    "コンビニ数",
    "スーパー数",
    "ドラッグストア数",
    "病院数",
    "駅数",
    "公園数",
    "学校数",
]

for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna().copy()

# ============================================
# 説明変数
# ============================================
FEATURES = [
    "コンビニ数",
    "スーパー数",
    "ドラッグストア数",
    "病院数",
    "駅数",
    "公園数",
    "学校数",
]

X = df[FEATURES]
y = df[TARGET_COL]

# ============================================
# 学習データ分割
# ============================================
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
)

# ============================================
# モデル学習
# ============================================
model = LinearRegression()
model.fit(X_train, y_train)

pred = model.predict(X_test)

# ============================================
# モデル評価
# ============================================
r2 = r2_score(y_test, pred)
rmse = math.sqrt(mean_squared_error(y_test, pred))

print("\n========================")
print("モデル評価")
print("========================")
print("R2:", round(r2, 4))
print("RMSE:", round(rmse, 4))

# ============================================
# 回帰係数
# ============================================
coef_df = pd.DataFrame({
    "変数": FEATURES,
    "係数": model.coef_,
}).sort_values("係数", ascending=False)

print("\n========================")
print("回帰係数")
print("========================")
print(coef_df)

# ============================================
# OLS
# ============================================
X2 = sm.add_constant(X)
ols = sm.OLS(y, X2).fit()

print("\n========================")
print("OLS Regression Results")
print("========================")
print(ols.summary())

# ============================================
# 全体予測・残差
# ============================================
df["予測値"] = model.predict(X)
df["残差"] = df[TARGET_COL] - df["予測値"]

df["zscore"] = (
    df["残差"] - df["残差"].mean()
) / df["残差"].std()

# ============================================
# 東京23区だけ抽出
# ============================================
tokyo_df = df[df["都市"] == "東京都"].copy()

# ============================================
# GeoJSON読み込み・結合
# ============================================
gdf = gpd.read_file(GEOJSON_FILE)

merged = gdf.merge(
    tokyo_df,
    left_on="ward_ja",
    right_on="区名",
    how="inner",
)

print("\n東京23区の結合件数:", len(merged))

# ============================================
# 区名ラベル用の代表点
# ============================================
merged["label_point"] = merged.geometry.representative_point()

# ============================================
# 見やすいZ-scoreヒートマップ
# ============================================
fig, ax = plt.subplots(figsize=(12, 12))

merged.plot(
    column="zscore",
    cmap="coolwarm",
    linewidth=0.8,
    edgecolor="black",
    legend=True,
    vmin=-2,
    vmax=2,
    ax=ax,
    legend_kwds={
        "label": "残差のZ-score（赤：予測より高い / 青：予測より低い）",
        "shrink": 0.65,
    },
)

# 区名ラベル
for _, row in merged.iterrows():
    ax.text(
        row["label_point"].x,
        row["label_point"].y,
        row["区名"].replace("区", ""),
        fontsize=8,
        ha="center",
        va="center",
    )

plt.title("東京23区 平均地価 残差Z-scoreマップ", fontsize=18)
plt.axis("off")
plt.tight_layout()
plt.savefig(OUT_DIR / "zscore_map_readable.png", dpi=300)
plt.close()

# ============================================
# 残差マップ：外れ値対策版
# ============================================
limit = merged["残差"].abs().quantile(0.90)

fig, ax = plt.subplots(figsize=(12, 12))

merged.plot(
    column="残差",
    cmap="coolwarm",
    linewidth=0.8,
    edgecolor="black",
    legend=True,
    vmin=-limit,
    vmax=limit,
    ax=ax,
    legend_kwds={
        "label": "残差（実測値 - 予測値）",
        "shrink": 0.65,
    },
)

for _, row in merged.iterrows():
    ax.text(
        row["label_point"].x,
        row["label_point"].y,
        row["区名"].replace("区", ""),
        fontsize=8,
        ha="center",
        va="center",
    )

plt.title("東京23区 平均地価 残差マップ", fontsize=18)
plt.axis("off")
plt.tight_layout()
plt.savefig(OUT_DIR / "residual_map_readable.png", dpi=300)
plt.close()

# ============================================
# 回帰係数グラフ
# ============================================
plt.figure(figsize=(10, 6))

plt.bar(coef_df["変数"], coef_df["係数"])
plt.axhline(0, linestyle="--", linewidth=1)

plt.xticks(rotation=45, ha="right")
plt.ylabel("係数")
plt.title("平均地価を予測する回帰係数")

plt.tight_layout()
plt.savefig(OUT_DIR / "coefficients.png", dpi=300)
plt.close()

# ============================================
# 実測 vs 予測
# ============================================
plt.figure(figsize=(7, 7))

plt.scatter(y_test, pred)

min_val = min(y_test.min(), pred.min())
max_val = max(y_test.max(), pred.max())

plt.plot(
    [min_val, max_val],
    [min_val, max_val],
    linestyle="--",
)

plt.xlabel("実測値")
plt.ylabel("予測値")
plt.title("平均地価 実測値 vs 予測値")

plt.tight_layout()
plt.savefig(OUT_DIR / "actual_vs_pred.png", dpi=300)
plt.close()

# ============================================
# 残差プロット
# ============================================
plt.figure(figsize=(7, 5))

plt.scatter(df["予測値"], df["残差"])
plt.axhline(0, linestyle="--")

plt.xlabel("予測値")
plt.ylabel("残差")
plt.title("残差プロット")

plt.tight_layout()
plt.savefig(OUT_DIR / "residual_plot.png", dpi=300)
plt.close()

# ============================================
# 相関行列
# ============================================
corr = df[numeric_cols].corr()

plt.figure(figsize=(10, 8))

plt.imshow(corr, aspect="auto")
plt.colorbar()

plt.xticks(
    range(len(corr.columns)),
    corr.columns,
    rotation=45,
    ha="right",
)

plt.yticks(
    range(len(corr.columns)),
    corr.columns,
)

plt.title("相関行列")

plt.tight_layout()
plt.savefig(OUT_DIR / "correlation_heatmap.png", dpi=300)
plt.close()

# ============================================
# 結果保存
# ============================================
result_df = df[
    [
        "都市",
        "区名",
        TARGET_COL,
        "予測値",
        "残差",
        "zscore",
    ]
]

result_df.to_csv(
    OUT_DIR / "residual_analysis.csv",
    index=False,
    encoding="utf-8-sig",
)

coef_df.to_csv(
    OUT_DIR / "coefficients.csv",
    index=False,
    encoding="utf-8-sig",
)

with open(OUT_DIR / "summary.txt", "w", encoding="utf-8") as f:
    f.write(ols.summary().as_text())

# ============================================
# 完了
# ============================================
print("\n========================")
print("分析完了")
print("========================")

print("\n出力先:")
print(OUT_DIR.resolve())

print("\n生成ファイル:")
for file in OUT_DIR.iterdir():
    print("-", file.name)