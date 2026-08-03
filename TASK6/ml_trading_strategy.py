#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TASK6: 基于机器学习模型的交易策略
==================================
1. 加载存储的模型样本数据 (model_data.csv)
2. 基于现有数据衍生模型自变量，设计模型预测应变量指标
3. 划分训练集/测试集（按时间），构建并训练多个ML模型
4. 基于模型建立交易策略，计算测试集中每个季度收益率
5. 回测策略，计算核心指标，绘制图形
6. 对比决策树、随机森林、逻辑回归、梯度提升等模型效果
"""

import os
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams

# 中文字体设置
rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'STHeiti', 'Arial Unicode MS']
rcParams['axes.unicode_minus'] = False

from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, roc_curve, confusion_matrix
)

# ============================================================
#  全局设置
# ============================================================
DATA_PATH = '/Users/wangyanfen/Downloads/model_data.csv'
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib_cache'
os.makedirs('/tmp/matplotlib_cache', exist_ok=True)

# 训练/测试时间分割点：2021Q3 之前为训练集，之后为测试集
TRAIN_CUTOFF = '2021/6/30'

# 策略参数：每季度选股数量
TOP_N = 50


# ============================================================
#  第一步：加载数据
# ============================================================
def load_data():
    """加载存储的模型样本数据"""
    print("=" * 70)
    print("  第一步：加载存储的模型样本数据")
    print("=" * 70)
    df = pd.read_csv(DATA_PATH)
    # 将日期标准化为季度末日期
    df['Date'] = pd.to_datetime(df['Date'], format='%Y/%m/%d')
    df = df.sort_values(['Date', 'Code']).reset_index(drop=True)
    print(f"  数据形状: {df.shape[0]} 行 x {df.shape[1]} 列")
    print(f"  时间范围: {df['Date'].min().strftime('%Y-%m-%d')} ~ {df['Date'].max().strftime('%Y-%m-%d')}")
    print(f"  季度数: {df['Date'].nunique()}")
    print(f"  股票数: {df['Code'].nunique()}")
    print(f"  列名: {list(df.columns)}")
    print(f"\n  Next_Ret 统计:")
    print(f"    均值: {df['Next_Ret'].mean():.4f}")
    print(f"    标准差: {df['Next_Ret'].std():.4f}")
    print(f"    最小值: {df['Next_Ret'].min():.4f}")
    print(f"    最大值: {df['Next_Ret'].max():.4f}")
    return df


# ============================================================
#  第二步：衍生模型自变量 & 设计应变量
# ============================================================
def feature_engineering(df):
    """
    基于现有数据衍生模型自变量因子，设计模型预测应变量指标

    自变量（特征）设计:
    --- 原始估值因子 (9个) ---
    企业倍数, 市净率PB, 市现率PCF(现金净流量), 市现率PCF(经营现金流),
    市盈率PE, 市盈率PE(扣非), 市销率PS, 股息率, MV

    --- 原始成长因子 (10个) ---
    净利润/净资产/利润总额/EPS/总资产/现金净流量/经营现金流/营业利润/营业总收入/营业收入 同比增长率

    --- 衍生因子 (新增) ---
    1. 估值综合排名 (valuation_rank): PE/PB/PS 三因子排名均值
    2. 成长综合排名 (growth_rank): 各成长因子排名均值
    3. 质量因子 (quality): 净利润增长率 - 总资产增长率（盈利增速 vs 扩张速度）
    4. 规模因子 (log_MV): 市值对数
    5. 估值偏离度 (pe_pb_diff): PE与PB变化方向是否一致
    6. 成长稳定性 (growth_stability): 多个成长因子的标准差倒数

    应变量设计:
    Y = 1 if Next_Ret > 季度截面中位数 else 0
    （即：下期收益跑赢同期市场中位数的股票标记为1，否则为0）
    """
    print("\n" + "=" * 70)
    print("  第二步：衍生模型自变量 & 设计应变量指标")
    print("=" * 70)

    df = df.copy()
    # 处理极端值：将无穷和超大值替换为NaN
    numeric_cols = df.select_dtypes(include=[np.floating]).columns
    df[numeric_cols] = df[numeric_cols].replace([np.inf, -np.inf], np.nan)

    # ---- 衍生因子 1: 估值综合排名 ----
    # 对PE, PB, PS在截面上排名（值越小排名越靠前=越便宜）
    for col in ['市盈率PE(TTM)', '市净率PB(MRQ)', '市销率PS(TTM)']:
        df[col + '_rank'] = df.groupby('Date')[col].rank(pct=True)
    df['valuation_rank'] = df[[
        '市盈率PE(TTM)_rank', '市净率PB(MRQ)_rank', '市销率PS(TTM)_rank'
    ]].mean(axis=1)

    # ---- 衍生因子 2: 成长综合排名 ----
    growth_cols = [
        '净利润同比增长率', '净资产同比增长率', '利润总额(同比增长率)',
        '基本每股收益(同比增长率)', '总资产同比增长率',
        '营业利润(同比增长率)', '营业总收入(同比增长率)', '营业收入(同比增长率)'
    ]
    for col in growth_cols:
        df[col + '_rank'] = df.groupby('Date')[col].rank(pct=True)
    df['growth_rank'] = df[[c + '_rank' for c in growth_cols]].mean(axis=1)

    # ---- 衍生因子 3: 质量因子 ----
    df['quality'] = df['净利润同比增长率'] - df['总资产同比增长率']

    # ---- 衍生因子 4: 规模因子 ----
    df['log_MV'] = np.log1p(df['MV'].clip(lower=0))

    # ---- 衍生因子 5: 估值偏离度 ----
    df['pe_pb_diff'] = df['市盈率PE(TTM)'] - df['市净率PB(MRQ)']

    # ---- 衍生因子 6: 成长稳定性（各成长因子的变异系数倒数） ----
    growth_std = df[growth_cols].std(axis=1)
    growth_mean = df[growth_cols].mean(axis=1).abs()
    df['growth_stability'] = growth_mean / (growth_std + 1)

    # ---- 衍生因子 7: 现金流质量 ----
    df['cashflow_quality'] = df['经营活动产生的现金流量净额(同比增长率)'] - df['净利润同比增长率']

    # ---- 应变量：下期收益是否跑赢截面中位数 ----
    df['ret_median'] = df.groupby('Date')['Next_Ret'].transform('median')
    df['Y'] = (df['Next_Ret'] > df['ret_median']).astype(int)

    # 清理缺失值
    df = df.dropna(subset=['Y'])

    # 定义特征列
    original_features = [
        '企业倍数(EV除EBITDA)', '市净率PB(MRQ)', '市现率PCF(现金净流量TTM)',
        '市现率PCF(经营现金流TTM)', '市盈率PE(TTM)', '市盈率PE(TTM,扣除非经常性损益)',
        '市销率PS(TTM)', '股息率(近12个月)', 'MV',
        '净利润同比增长率', '净资产同比增长率', '利润总额(同比增长率)',
        '基本每股收益(同比增长率)', '总资产同比增长率', '现金净流量同比增长率',
        '经营活动产生的现金流量净额(同比增长率)', '营业利润(同比增长率)',
        '营业总收入(同比增长率)', '营业收入(同比增长率)'
    ]
    derived_features = [
        'valuation_rank', 'growth_rank', 'quality', 'log_MV',
        'pe_pb_diff', 'growth_stability', 'cashflow_quality'
    ]
    all_features = original_features + derived_features

    print(f"\n  原始特征 ({len(original_features)} 个): 估值因子 + 成长因子")
    print(f"  衍生特征 ({len(derived_features)} 个):")
    for f in derived_features:
        print(f"    - {f}")
    print(f"  特征总数: {len(all_features)}")
    print(f"\n  应变量 Y: 下期收益 > 季度截面中位数 → 1, 否则 → 0")
    print(f"  Y 分布:\n{df['Y'].value_counts(normalize=True).to_string()}")

    return df, all_features


# ============================================================
#  第三步：划分训练集/测试集 & 构建训练模型
# ============================================================
def split_and_train(df, features):
    """按时间划分训练集/测试集，构建并训练多个模型"""
    print("\n" + "=" * 70)
    print("  第三步：划分训练集/测试集，构建并训练模型")
    print("=" * 70)

    cutoff_date = pd.to_datetime(TRAIN_CUTOFF)

    train_df = df[df['Date'] <= cutoff_date].copy()
    test_df = df[df['Date'] > cutoff_date].copy()

    print(f"\n  训练集: {train_df['Date'].min().strftime('%Y-%m-%d')} ~ "
          f"{train_df['Date'].max().strftime('%Y-%m-%d')}")
    print(f"    样本数: {len(train_df)}, 正样本占比: {train_df['Y'].mean():.2%}")
    print(f"  测试集: {test_df['Date'].min().strftime('%Y-%m-%d')} ~ "
          f"{test_df['Date'].max().strftime('%Y-%m-%d')}")
    print(f"    样本数: {len(test_df)}, 正样本占比: {test_df['Y'].mean():.2%}")

    # 准备特征矩阵
    X_train = train_df[features].values
    y_train = train_df['Y'].values
    X_test = test_df[features].values
    y_test = test_df['Y'].values

    # 特征标准化
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # 构建模型
    models = {
        '逻辑回归': LogisticRegression(max_iter=2000, C=1.0, random_state=42),
        '决策树': DecisionTreeClassifier(max_depth=6, min_samples_leaf=50,
                                        random_state=42),
        '随机森林': RandomForestClassifier(n_estimators=200, max_depth=10,
                                        min_samples_leaf=20, random_state=42,
                                        n_jobs=-1),
        '梯度提升': GradientBoostingClassifier(n_estimators=150, max_depth=5,
                                             learning_rate=0.1,
                                             subsample=0.8, random_state=42),
    }

    results = {}
    for name, model in models.items():
        print(f"\n  --- 训练 {name} ---")
        if name == '逻辑回归':
            model.fit(X_train_scaled, y_train)
            y_pred = model.predict(X_test_scaled)
            y_prob = model.predict_proba(X_test_scaled)[:, 1]
        else:
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            y_prob = model.predict_proba(X_test)[:, 1]

        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        auc = roc_auc_score(y_test, y_prob)

        print(f"    准确率: {acc:.4f}")
        print(f"    精确率: {prec:.4f}")
        print(f"    召回率: {rec:.4f}")
        print(f"    F1值:   {f1:.4f}")
        print(f"    AUC:    {auc:.4f}")

        results[name] = {
            'model': model,
            'scaler': scaler if name == '逻辑回归' else None,
            'y_pred': y_pred,
            'y_prob': y_prob,
            'accuracy': acc,
            'precision': prec,
            'recall': rec,
            'f1': f1,
            'auc': auc,
        }

    return train_df, test_df, features, results, scaler


# ============================================================
#  第四步 & 第五步：构建交易策略 & 回测
# ============================================================
def build_strategy_and_backtest(test_df, features, results, scaler):
    """
    基于模型建立交易策略，计算测试集中每个季度收益率，
    回测策略，计算核心指标。
    """
    print("\n" + "=" * 70)
    print("  第四步 & 第五步：构建交易策略 & 回测")
    print("=" * 70)

    test_quarters = sorted(test_df['Date'].unique())
    print(f"\n  测试集季度: {[d.strftime('%Y-%m') for d in test_quarters]}")
    print(f"  策略: 每季度选模型预测概率最高的 {TOP_N} 只股票，等权持有")

    # 为每个模型生成预测概率
    strategy_returns = {}

    for model_name, res in results.items():
        model = res['model']
        scaler_model = res['scaler']

        # 在测试集上生成预测概率
        if scaler_model is not None:
            X_test = scaler_model.transform(test_df[features].values)
        else:
            X_test = test_df[features].values

        probs = model.predict_proba(X_test)[:, 1]
        test_df_copy = test_df.copy()
        test_df_copy['pred_prob'] = probs

        # 逐季度构建组合
        quarterly_returns = []
        portfolio_stocks = []

        for q_date in test_quarters:
            q_data = test_df_copy[test_df_copy['Date'] == q_date].copy()
            # 选预测概率最高的 TOP_N 只
            top_stocks = q_data.nlargest(TOP_N, 'pred_prob')
            # 等权组合收益
            port_ret = top_stocks['Next_Ret'].mean()
            # 基准：全市场等权
            bench_ret = q_data['Next_Ret'].mean()

            quarterly_returns.append({
                'quarter': q_date,
                'portfolio_ret': port_ret,
                'benchmark_ret': bench_ret,
                'excess_ret': port_ret - bench_ret,
                'n_stocks': len(top_stocks),
            })
            portfolio_stocks.append(top_stocks)

        ret_df = pd.DataFrame(quarterly_returns)
        strategy_returns[model_name] = ret_df

        # 打印季度收益
        print(f"\n  --- {model_name} 季度收益 ---")
        print(f"  {'季度':<12} {'组合收益':>10} {'基准收益':>10} {'超额收益':>10}")
        print("  " + "-" * 46)
        for _, row in ret_df.iterrows():
            q_str = row['quarter'].strftime('%Y-%m')
            print(f"  {q_str:<12} {row['portfolio_ret']:>10.4f} "
                  f"{row['benchmark_ret']:>10.4f} {row['excess_ret']:>10.4f}")

    return strategy_returns


def calculate_metrics(strategy_returns):
    """计算回测核心指标"""
    print("\n" + "=" * 70)
    print("  回测核心指标")
    print("=" * 70)

    all_metrics = {}
    for model_name, ret_df in strategy_returns.items():
        port_rets = ret_df['portfolio_ret'].values
        bench_rets = ret_df['benchmark_ret'].values
        excess_rets = ret_df['excess_ret'].values

        # 累计收益
        cum_port = np.cumprod(1 + port_rets) - 1
        cum_bench = np.cumprod(1 + bench_rets) - 1

        # 年化收益（每季度 = 0.25年）
        n_quarters = len(port_rets)
        years = n_quarters / 4
        ann_port = (1 + cum_port[-1]) ** (1 / years) - 1 if years > 0 else 0
        ann_bench = (1 + cum_bench[-1]) ** (1 / years) - 1 if years > 0 else 0

        # 夏普比率（季度 -> 年化: *sqrt(4)）
        sharpe_port = np.mean(port_rets) / (np.std(port_rets) + 1e-10) * np.sqrt(4)
        sharpe_bench = np.mean(bench_rets) / (np.std(bench_rets) + 1e-10) * np.sqrt(4)
        sharpe_excess = np.mean(excess_rets) / (np.std(excess_rets) + 1e-10) * np.sqrt(4)

        # 最大回撤
        cum_curve = np.cumprod(1 + port_rets)
        peak = np.maximum.accumulate(cum_curve)
        drawdown = (cum_curve - peak) / peak
        max_dd = drawdown.min()

        # 胜率
        win_rate = np.mean(excess_rets > 0)

        # 平均季度超额收益
        avg_excess = np.mean(excess_rets)

        metrics = {
            '累计收益': cum_port[-1],
            '年化收益': ann_port,
            '夏普比率': sharpe_port,
            '最大回撤': max_dd,
            '胜率': win_rate,
            '平均超额': avg_excess,
            '超额夏普': sharpe_excess,
            '基准累计': cum_bench[-1],
            '基准年化': ann_bench,
            '基准夏普': sharpe_bench,
        }
        all_metrics[model_name] = metrics

    # 打印汇总表
    print(f"\n  {'模型':<12} {'累计收益':>10} {'年化收益':>10} {'夏普比率':>10} "
          f"{'最大回撤':>10} {'胜率':>8} {'超额夏普':>10}")
    print("  " + "-" * 74)
    for model_name, m in all_metrics.items():
        print(f"  {model_name:<12} {m['累计收益']:>10.2%} {m['年化收益']:>10.2%} "
              f"{m['夏普比率']:>10.4f} {m['最大回撤']:>10.2%} {m['胜率']:>8.2%} "
              f"{m['超额夏普']:>10.4f}")
    print(f"\n  基准(全市场等权): 累计={all_metrics[list(all_metrics.keys())[0]]['基准累计']:.2%}, "
          f"年化={all_metrics[list(all_metrics.keys())[0]]['基准年化']:.2%}, "
          f"夏普={all_metrics[list(all_metrics.keys())[0]]['基准夏普']:.4f}")

    return all_metrics


# ============================================================
#  第六步：对比模型效果 & 绘制图形
# ============================================================
def plot_results(strategy_returns, all_metrics, results, features, test_df):
    """绘制对比图形"""
    print("\n" + "=" * 70)
    print("  第六步：对比模型效果 & 绘制图形")
    print("=" * 70)

    colors = {
        '逻辑回归': '#e74c3c',
        '决策树': '#2ecc71',
        '随机森林': '#3498db',
        '梯度提升': '#f39c12',
    }

    # ---- 图1: 累计收益曲线 ----
    fig1, ax1 = plt.subplots(figsize=(12, 6))
    for model_name, ret_df in strategy_returns.items():
        cum = np.cumprod(1 + ret_df['portfolio_ret'].values) - 1
        quarters = [d.strftime('%Y-Q%q') for d in ret_df['quarter']]
        # 生成季度标签
        qlabels = [d.strftime('%Y-%m') for d in ret_df['quarter']]
        ax1.plot(range(len(cum)), cum, marker='o', linewidth=2.5,
                 color=colors.get(model_name, 'gray'), label=model_name)
    # 基准线
    bench_cum = np.cumprod(1 + strategy_returns[list(strategy_returns.keys())[0]]['benchmark_ret'].values) - 1
    ax1.plot(range(len(bench_cum)), bench_cum, marker='s', linewidth=2,
             color='#95a5a6', linestyle='--', label='基准(全市场等权)')
    ax1.set_xticks(range(len(qlabels)))
    ax1.set_xticklabels(qlabels, fontsize=11)
    ax1.set_ylabel('累计收益率', fontsize=13)
    ax1.set_title('各模型交易策略 - 累计收益曲线对比', fontsize=15, fontweight='bold')
    ax1.legend(fontsize=11, loc='upper left')
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=0, color='black', linewidth=0.5)
    fig1.tight_layout()
    path1 = os.path.join(OUTPUT_DIR, 'cumulative_returns.png')
    fig1.savefig(path1, dpi=150, bbox_inches='tight')
    plt.close(fig1)
    print(f"  [已保存] {path1}")

    # ---- 图2: 季度收益柱状图 ----
    fig2, ax2 = plt.subplots(figsize=(12, 6))
    model_names = list(strategy_returns.keys())
    n_models = len(model_names)
    n_quarters = len(strategy_returns[model_names[0]])
    x = np.arange(n_quarters)
    width = 0.18
    for i, name in enumerate(model_names):
        rets = strategy_returns[name]['portfolio_ret'].values
        bars = ax2.bar(x + i * width, rets, width,
                       color=colors.get(name, 'gray'), label=name)
        for bar, val in zip(bars, rets):
            color = 'red' if val > 0 else 'green'
            ax2.text(bar.get_x() + bar.get_width()/2,
                     bar.get_height() + 0.003 if val > 0 else bar.get_height() - 0.008,
                     f'{val:.1%}', ha='center', va='bottom' if val > 0 else 'top',
                     fontsize=7, color=color, fontweight='bold')
    ax2.set_xticks(x + width * (n_models - 1) / 2)
    qlabels = [d.strftime('%Y-%m') for d in strategy_returns[model_names[0]]['quarter']]
    ax2.set_xticklabels(qlabels, fontsize=11)
    ax2.set_ylabel('季度收益率', fontsize=13)
    ax2.set_title('各模型交易策略 - 季度收益率对比', fontsize=15, fontweight='bold')
    ax2.legend(fontsize=11)
    ax2.grid(True, axis='y', alpha=0.3)
    ax2.axhline(y=0, color='black', linewidth=0.5)
    fig2.tight_layout()
    path2 = os.path.join(OUTPUT_DIR, 'quarterly_returns.png')
    fig2.savefig(path2, dpi=150, bbox_inches='tight')
    plt.close(fig2)
    print(f"  [已保存] {path2}")

    # ---- 图3: 超额收益柱状图 ----
    fig3, ax3 = plt.subplots(figsize=(12, 6))
    for i, name in enumerate(model_names):
        excess = strategy_returns[name]['excess_ret'].values
        bars = ax3.bar(x + i * width, excess, width,
                       color=colors.get(name, 'gray'), label=name)
    ax3.set_xticks(x + width * (n_models - 1) / 2)
    ax3.set_xticklabels(qlabels, fontsize=11)
    ax3.set_ylabel('超额收益率', fontsize=13)
    ax3.set_title('各模型交易策略 - 季度超额收益（vs 基准）', fontsize=15, fontweight='bold')
    ax3.legend(fontsize=11)
    ax3.grid(True, axis='y', alpha=0.3)
    ax3.axhline(y=0, color='black', linewidth=1)
    fig3.tight_layout()
    path3 = os.path.join(OUTPUT_DIR, 'excess_returns.png')
    fig3.savefig(path3, dpi=150, bbox_inches='tight')
    plt.close(fig3)
    print(f"  [已保存] {path3}")

    # ---- 图4: 模型评估指标对比柱状图 ----
    fig4, ax4 = plt.subplots(figsize=(12, 6))
    metric_names = ['准确率', '精确率', '召回率', 'F1值', 'AUC']
    x4 = np.arange(len(metric_names))
    width4 = 0.18
    for i, name in enumerate(model_names):
        r = results[name]
        values = [r['accuracy'], r['precision'], r['recall'], r['f1'], r['auc']]
        bars = ax4.bar(x4 + i * width4, values, width4,
                       color=colors.get(name, 'gray'), label=name)
        for bar, val in zip(bars, values):
            ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                     f'{val:.3f}', ha='center', va='bottom', fontsize=7)
    ax4.set_xticks(x4 + width4 * (n_models - 1) / 2)
    ax4.set_xticklabels(metric_names, fontsize=12)
    ax4.set_ylim([0, 1.08])
    ax4.set_ylabel('分数', fontsize=13)
    ax4.set_title('各模型分类评估指标对比', fontsize=15, fontweight='bold')
    ax4.legend(fontsize=11)
    ax4.grid(True, axis='y', alpha=0.3)
    fig4.tight_layout()
    path4 = os.path.join(OUTPUT_DIR, 'model_metrics.png')
    fig4.savefig(path4, dpi=150, bbox_inches='tight')
    plt.close(fig4)
    print(f"  [已保存] {path4}")

    # ---- 图5: ROC 曲线 ----
    fig5, ax5 = plt.subplots(figsize=(8, 7))
    y_test = test_df['Y'].values
    for name in model_names:
        r = results[name]
        fpr, tpr, _ = roc_curve(y_test, r['y_prob'])
        ax5.plot(fpr, tpr, linewidth=2.5, color=colors.get(name, 'gray'),
                 label=f'{name} (AUC={r["auc"]:.4f})')
    ax5.plot([0, 1], [0, 1], 'k--', linewidth=1, alpha=0.5, label='随机分类器')
    ax5.set_xlabel('假正率 (FPR)', fontsize=13)
    ax5.set_ylabel('真正率 (TPR)', fontsize=13)
    ax5.set_title('各模型 ROC 曲线对比', fontsize=15, fontweight='bold')
    ax5.legend(fontsize=11, loc='lower right')
    ax5.set_xlim([-0.01, 1.01])
    ax5.set_ylim([-0.01, 1.01])
    ax5.grid(True, alpha=0.3)
    fig5.tight_layout()
    path5 = os.path.join(OUTPUT_DIR, 'roc_curves.png')
    fig5.savefig(path5, dpi=150, bbox_inches='tight')
    plt.close(fig5)
    print(f"  [已保存] {path5}")

    # ---- 图6: 回测核心指标雷达图/柱状图 ----
    fig6, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig6.suptitle('各模型回测核心指标对比', fontsize=16, fontweight='bold')

    # 累计收益
    ax = axes[0, 0]
    vals = [all_metrics[n]['累计收益'] for n in model_names]
    bars = ax.bar(model_names, vals, color=[colors.get(n, 'gray') for n in model_names])
    ax.set_title('累计收益率', fontsize=13, fontweight='bold')
    ax.axhline(y=all_metrics[model_names[0]]['基准累计'], color='gray',
              linestyle='--', label=f'基准={all_metrics[model_names[0]]["基准累计"]:.2%}')
    ax.legend(fontsize=10)
    ax.grid(True, axis='y', alpha=0.3)
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.002,
                f'{val:.2%}', ha='center', va='bottom', fontsize=10, fontweight='bold')

    # 年化收益
    ax = axes[0, 1]
    vals = [all_metrics[n]['年化收益'] for n in model_names]
    bars = ax.bar(model_names, vals, color=[colors.get(n, 'gray') for n in model_names])
    ax.set_title('年化收益率', fontsize=13, fontweight='bold')
    ax.axhline(y=all_metrics[model_names[0]]['基准年化'], color='gray',
              linestyle='--', label=f'基准={all_metrics[model_names[0]]["基准年化"]:.2%}')
    ax.legend(fontsize=10)
    ax.grid(True, axis='y', alpha=0.3)
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.002,
                f'{val:.2%}', ha='center', va='bottom', fontsize=10, fontweight='bold')

    # 夏普比率
    ax = axes[1, 0]
    vals = [all_metrics[n]['夏普比率'] for n in model_names]
    bars = ax.bar(model_names, vals, color=[colors.get(n, 'gray') for n in model_names])
    ax.set_title('夏普比率', fontsize=13, fontweight='bold')
    ax.axhline(y=all_metrics[model_names[0]]['基准夏普'], color='gray',
              linestyle='--', label=f'基准={all_metrics[model_names[0]]["基准夏普"]:.4f}')
    ax.legend(fontsize=10)
    ax.grid(True, axis='y', alpha=0.3)
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f'{val:.4f}', ha='center', va='bottom', fontsize=10, fontweight='bold')

    # 最大回撤
    ax = axes[1, 1]
    vals = [all_metrics[n]['最大回撤'] for n in model_names]
    bars = ax.bar(model_names, vals, color=[colors.get(n, 'gray') for n in model_names])
    ax.set_title('最大回撤', fontsize=13, fontweight='bold')
    ax.grid(True, axis='y', alpha=0.3)
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() - 0.005,
                f'{val:.2%}', ha='center', va='top', fontsize=10, fontweight='bold')

    fig6.tight_layout(rect=[0, 0, 1, 0.95])
    path6 = os.path.join(OUTPUT_DIR, 'backtest_metrics.png')
    fig6.savefig(path6, dpi=150, bbox_inches='tight')
    plt.close(fig6)
    print(f"  [已保存] {path6}")

    # ---- 图7: 特征重要性（随机森林） ----
    rf_model = results.get('随机森林', {}).get('model')
    if rf_model is not None:
        fig7, ax7 = plt.subplots(figsize=(10, 8))
        importances = rf_model.feature_importances_
        indices = np.argsort(importances)[::-1]
        top_n = min(15, len(features))
        ax7.barh(range(top_n), [importances[i] for i in indices[:top_n]],
                 color='#3498db', alpha=0.8)
        ax7.set_yticks(range(top_n))
        ax7.set_yticklabels([features[i] for i in indices[:top_n]], fontsize=11)
        ax7.invert_yaxis()
        ax7.set_xlabel('特征重要性', fontsize=13)
        ax7.set_title('随机森林 - 特征重要性 Top15', fontsize=15, fontweight='bold')
        ax7.grid(True, axis='x', alpha=0.3)
        fig7.tight_layout()
        path7 = os.path.join(OUTPUT_DIR, 'feature_importance.png')
        fig7.savefig(path7, dpi=150, bbox_inches='tight')
        plt.close(fig7)
        print(f"  [已保存] {path7}")

    return [path1, path2, path3, path4, path5, path6] + ([path7] if rf_model else [])


# ============================================================
#  附加题：使用回归模型预测收益率 + 不同选股策略
# ============================================================
def bonus_regression_strategy(df, features):
    """
    附加题：使用回归模型直接预测下期收益率，
    并基于预测值排序构建投资策略，对比不同模型。
    """
    print("\n" + "=" * 70)
    print("  附加题：回归模型预测收益率 + 动量策略回测")
    print("=" * 70)

    from sklearn.linear_model import LinearRegression, Ridge
    from sklearn.tree import DecisionTreeRegressor
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.metrics import mean_squared_error, r2_score

    cutoff_date = pd.to_datetime(TRAIN_CUTOFF)
    train_df = df[df['Date'] <= cutoff_date].copy()
    test_df = df[df['Date'] > cutoff_date].copy()

    X_train = train_df[features].values
    y_train = train_df['Next_Ret'].values
    X_test = test_df[features].values
    y_test = test_df['Next_Ret'].values

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    reg_models = {
        '线性回归': LinearRegression(),
        '岭回归': Ridge(alpha=1.0),
        '决策树回归': DecisionTreeRegressor(max_depth=6, random_state=42),
        '随机森林回归': RandomForestRegressor(n_estimators=150, max_depth=10,
                                           random_state=42, n_jobs=-1),
        '梯度提升回归': GradientBoostingRegressor(n_estimators=150, max_depth=5,
                                              learning_rate=0.1, random_state=42),
    }

    reg_results = {}
    test_quarters = sorted(test_df['Date'].unique())

    for name, model in reg_models.items():
        print(f"\n  --- 训练 {name} ---")
        if name in ('线性回归', '岭回归'):
            model.fit(X_train_s, y_train)
            preds = model.predict(X_test_s)
        else:
            model.fit(X_train, y_train)
            preds = model.predict(X_test)

        mse = mean_squared_error(y_test, preds)
        r2 = r2_score(y_test, preds)
        ic = np.corrcoef(preds, y_test)[0, 1]
        print(f"    MSE: {mse:.6f}")
        print(f"    R²:  {r2:.4f}")
        print(f"    IC(相关系数): {ic:.4f}")

        # 构建策略：每季度选预测收益最高的TOP_N只
        test_copy = test_df.copy()
        test_copy['pred_ret'] = preds

        quarterly_returns = []
        for q_date in test_quarters:
            q_data = test_copy[test_copy['Date'] == q_date]
            top = q_data.nlargest(TOP_N, 'pred_ret')
            port_ret = top['Next_Ret'].mean()
            bench_ret = q_data['Next_Ret'].mean()
            # 底部组合（反向）
            bottom = q_data.nsmallest(TOP_N, 'pred_ret')
            bottom_ret = bottom['Next_Ret'].mean()
            quarterly_returns.append({
                'quarter': q_date,
                'portfolio_ret': port_ret,
                'benchmark_ret': bench_ret,
                'bottom_ret': bottom_ret,
                'excess_ret': port_ret - bench_ret,
                'long_short': port_ret - bottom_ret,
            })

        ret_df = pd.DataFrame(quarterly_returns)
        cum = np.cumprod(1 + ret_df['portfolio_ret'].values) - 1
        cum_bench = np.cumprod(1 + ret_df['benchmark_ret'].values) - 1
        cum_ls = np.cumprod(1 + ret_df['long_short'].values) - 1
        n_q = len(ret_df)
        years = n_q / 4
        ann_ret = (1 + cum[-1]) ** (1 / years) - 1 if years > 0 else 0
        sharpe = np.mean(ret_df['portfolio_ret']) / (np.std(ret_df['portfolio_ret']) + 1e-10) * np.sqrt(4)
        win_rate = np.mean(ret_df['excess_ret'] > 0)
        cum_curve = np.cumprod(1 + ret_df['portfolio_ret'].values)
        peak = np.maximum.accumulate(cum_curve)
        max_dd = ((cum_curve - peak) / peak).min()

        reg_results[name] = {
            'mse': mse, 'r2': r2, 'ic': ic,
            'cum_ret': cum[-1], 'ann_ret': ann_ret,
            'sharpe': sharpe, 'max_dd': max_dd,
            'win_rate': win_rate,
            'ret_df': ret_df,
            'cum_curve': cum,
            'cum_bench': cum_bench,
            'cum_ls': cum_ls,
        }

    # 打印汇总
    print(f"\n  {'模型':<14} {'MSE':>10} {'R²':>8} {'IC':>8} {'累计收益':>10} "
          f"{'年化收益':>10} {'夏普':>8} {'最大回撤':>10} {'胜率':>8}")
    print("  " + "-" * 82)
    for name, r in reg_results.items():
        print(f"  {name:<14} {r['mse']:>10.6f} {r['r2']:>8.4f} {r['ic']:>8.4f} "
              f"{r['cum_ret']:>10.2%} {r['ann_ret']:>10.2%} {r['sharpe']:>8.4f} "
              f"{r['max_dd']:>10.2%} {r['win_rate']:>8.2%}")

    # ---- 绘图：回归模型累计收益 ----
    colors_reg = {
        '线性回归': '#e74c3c', '岭回归': '#9b59b6', '决策树回归': '#2ecc71',
        '随机森林回归': '#3498db', '梯度提升回归': '#f39c12',
    }
    fig, ax = plt.subplots(figsize=(12, 6))
    for name, r in reg_results.items():
        ax.plot(range(len(r['cum_curve'])), r['cum_curve'], marker='o',
                linewidth=2.5, color=colors_reg.get(name, 'gray'), label=name)
    # 基准
    first_model = list(reg_results.keys())[0]
    bench = reg_results[first_model]['cum_bench']
    ax.plot(range(len(bench)), bench, marker='s', linewidth=2,
            color='#95a5a6', linestyle='--', label='基准(全市场等权)')
    qlabels = [d.strftime('%Y-%m') for d in test_quarters]
    ax.set_xticks(range(len(qlabels)))
    ax.set_xticklabels(qlabels, fontsize=11)
    ax.set_ylabel('累计收益率', fontsize=13)
    ax.set_title('附加题：回归模型交易策略 - 累计收益对比', fontsize=15, fontweight='bold')
    ax.legend(fontsize=11, loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color='black', linewidth=0.5)
    fig.tight_layout()
    path_reg = os.path.join(OUTPUT_DIR, 'bonus_regression_returns.png')
    fig.savefig(path_reg, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"\n  [已保存] {path_reg}")

    # ---- 绘图：多空组合累计收益 ----
    fig2, ax2 = plt.subplots(figsize=(12, 6))
    for name, r in reg_results.items():
        ax2.plot(range(len(r['cum_ls'])), r['cum_ls'], marker='o',
                 linewidth=2.5, color=colors_reg.get(name, 'gray'),
                 label=f'{name} (多空)')
    ax2.set_xticks(range(len(qlabels)))
    ax2.set_xticklabels(qlabels, fontsize=11)
    ax2.set_ylabel('多空累计收益', fontsize=13)
    ax2.set_title('附加题：多空组合（做多Top50 + 做空Bottom50）累计收益', fontsize=15, fontweight='bold')
    ax2.legend(fontsize=11)
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=0, color='black', linewidth=0.5)
    fig2.tight_layout()
    path_ls = os.path.join(OUTPUT_DIR, 'bonus_long_short.png')
    fig2.savefig(path_ls, dpi=150, bbox_inches='tight')
    plt.close(fig2)
    print(f"  [已保存] {path_ls}")

    # ---- 绘图：IC 对比 ----
    fig3, ax3 = plt.subplots(figsize=(10, 6))
    names = list(reg_results.keys())
    ics = [reg_results[n]['ic'] for n in names]
    bars = ax3.bar(names, ics, color=[colors_reg.get(n, 'gray') for n in names])
    ax3.set_ylabel('IC (信息系数)', fontsize=13)
    ax3.set_title('附加题：各回归模型 IC 对比', fontsize=15, fontweight='bold')
    ax3.grid(True, axis='y', alpha=0.3)
    ax3.axhline(y=0, color='black', linewidth=0.5)
    for bar, val in zip(bars, ics):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.002,
                 f'{val:.4f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    fig3.tight_layout()
    path_ic = os.path.join(OUTPUT_DIR, 'bonus_ic_compare.png')
    fig3.savefig(path_ic, dpi=150, bbox_inches='tight')
    plt.close(fig3)
    print(f"  [已保存] {path_ic}")

    return reg_results, [path_reg, path_ls, path_ic]


# ============================================================
#  主程序
# ============================================================
def main():
    print("\n" + "#" * 70)
    print("#  TASK6: 基于机器学习模型的交易策略")
    print("#" * 70)

    # Step 1: 加载数据
    df = load_data()

    # Step 2: 特征工程
    df, features = feature_engineering(df)

    # Step 3: 划分 & 训练
    train_df, test_df, features, results, scaler = split_and_train(df, features)

    # Step 4 & 5: 策略 & 回测
    strategy_returns = build_strategy_and_backtest(test_df, features, results, scaler)

    # 回测指标
    all_metrics = calculate_metrics(strategy_returns)

    # Step 6: 绘图
    plot_paths = plot_results(strategy_returns, all_metrics, results, features, test_df)

    # 附加题
    reg_results, bonus_paths = bonus_regression_strategy(df, features)

    # 汇总
    print("\n" + "=" * 70)
    print("  全部完成！输出文件:")
    print("=" * 70)
    for f in sorted(os.listdir(OUTPUT_DIR)):
        if f.endswith('.png'):
            print(f"  - {f}")

    # 保存汇总指标到 CSV
    metrics_rows = []
    for model_name, m in all_metrics.items():
        metrics_rows.append({
            '模型': model_name,
            '累计收益': f"{m['累计收益']:.4f}",
            '年化收益': f"{m['年化收益']:.4f}",
            '夏普比率': f"{m['夏普比率']:.4f}",
            '最大回撤': f"{m['最大回撤']:.4f}",
            '胜率': f"{m['胜率']:.4f}",
            '超额夏普': f"{m['超额夏普']:.4f}",
        })
    metrics_df = pd.DataFrame(metrics_rows)
    metrics_df.to_csv(os.path.join(OUTPUT_DIR, 'backtest_metrics.csv'), index=False,
                      encoding='utf-8-sig')
    print(f"\n  回测指标已保存: backtest_metrics.csv")


if __name__ == '__main__':
    main()
