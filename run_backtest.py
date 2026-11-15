"""
CLI Runner for the Autonomous AI Gold Strategy Backtester
Usage:
  python run_backtest.py
  python run_backtest.py --start 2026-07-01 --end 2026-11-15 --balance 10000 --risk 1.0
"""

import sys
import argparse
from src.backtester import GoldBacktester

def main():
    parser = argparse.ArgumentParser(description="Autonomous AI Gold Strategy Backtester")
    parser.add_argument("--start", type=str, default="2026-07-01", help="Start Date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, default="2026-11-15", help="End Date (YYYY-MM-DD)")
    parser.add_argument("--balance", type=float, default=10000.0, help="Initial Account Balance in USD (default: 10000)")
    parser.add_argument("--risk", type=float, default=1.0, help="Risk percentage per trade (default: 1.0 percent)")
    parser.add_argument("--sl", type=float, default=150.0, help="Stop loss in pips (default: 150)")
    parser.add_argument("--tp1", type=float, default=120.0, help="Target 1 in pips (default: 120)")
    parser.add_argument("--tp2", type=float, default=260.0, help="Target 2 in pips (default: 260)")

    args = parser.parse_args()

    backtester = GoldBacktester(
        initial_balance=args.balance,
        risk_pct=args.risk,
        sl_pips=args.sl,
        tp1_pips=args.tp1,
        tp2_pips=args.tp2
    )

    print("=" * 80)
    print(f"📊 BACKTEST CONFIGURATION: {args.start} to {args.end}")
    print(f"Account Balance:   ${args.balance:,.2f}")
    print(f"Risk per Trade:    {args.risk}%")
    print(f"Order Parameters:  SL: {args.sl}p | TP1: {args.tp1}p | TP2: {args.tp2}p")
    print("=" * 80)

    candles = backtester.fetch_historical_candles(args.start, args.end)
    if not candles:
        print("No historical data found. Exiting.")
        sys.exit(1)

    results = backtester.run_backtest(candles)

    # Pretty-print performance report
    bold = "\033[1m"
    green = "\033[92m"
    red = "\033[91m"
    reset = "\033[0m"

    ret_color = green if results["net_profit_dollars"] >= 0 else red

    print("\n" + "=" * 80)
    print(f"{bold}📈 HISTORICAL PERFORMANCE REPORT ({args.start} to {args.end}){reset}")
    print("=" * 80)
    print(f"  {bold}Initial Capital:{reset}       ${results['initial_balance']:,.2f}")
    print(f"  {bold}Final Capital:{reset}         ${results['final_balance']:,.2f}")
    print(f"  {bold}Net Profit:{reset}            {ret_color}${results['net_profit_dollars']:,.2f} ({results['net_return_pct']:+.2f}%){reset}")
    print(f"  {bold}Total Trades Taken:{reset}    {results['total_trades']}")
    print(f"  {bold}Winning Trades:{reset}        {results['winning_trades']} ({results['win_rate_pct']}%)")
    print(f"  {bold}Losing Trades:{reset}         {results['losing_trades']}")
    print(f"  {bold}Profit Factor:{reset}         {results['profit_factor']}")
    print(f"  {bold}Max Drawdown:{reset}          {red}{results['max_drawdown_pct']:.2f}% (${results['max_drawdown_dollars']:,.2f}){reset}")
    print(f"  {bold}Average Win:{reset}           ${results['avg_win_dollars']:,.2f}")
    print(f"  {bold}Average Loss:{reset}          ${results['avg_loss_dollars']:,.2f}")
    print("=" * 80)

    # Print last 5 simulated trades
    print(f"\n{bold}Recent 5 Simulated Trades:{reset}")
    for t in results["trades"][-5:]:
        color = green if t["pnl"] > 0 else red
        print(f"  Trade #{t['trade_num']} [{t['entry_date'][:16]}] {t['direction']} @ ${t['entry']:.2f} -> Exit @ ${t['exit_price']:.2f} | PnL: {color}{t['pnl']:+,.2f} ({t['pnl_pips']:+.0f}p){reset} | Outcome: {t['outcome']}")

if __name__ == "__main__":
    main()
