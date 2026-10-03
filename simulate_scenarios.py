from simulation import SimulationInputs, find_required_portfolio, find_required_contribution

current_age = 22
initial_savings = 50_000_000
house_price = 1_000_000_000
spending_today = 8_000_000
inflation = 0.03
stock_alloc = 0.60
stock_return = 0.07
stock_std = 0.14
bond_return = 0.30
bond_std = 0.23
blended_return = stock_alloc * stock_return + (1 - stock_alloc) * bond_return
house_return = 0.055
success_rate = 0.80
r_house = house_return / 12

# SCENARIO 1: Both at 50
retire_age_1 = 50
house_age_1 = 50
house_years_1 = retire_age_1 - current_age
house_months_1 = house_years_1 * 12

pmt_house_s1 = house_price * r_house / ((1 + r_house)**house_months_1 - 1)
spending_at_50 = spending_today * (1 + inflation)**house_years_1

inputs_s1 = SimulationInputs(
    initial_portfolio=10_000_000_000, monthly_spending=spending_at_50,
    inflation=inflation, stock_allocation=stock_alloc,
    stock_return=stock_return, stock_std=stock_std,
    bond_return=bond_return, bond_std=bond_std,
    retirement_age=retire_age_1, death_age=85,
    num_simulations=5000, seed=42,
)
result_s1 = find_required_portfolio(inputs_s1, target_success_rate=success_rate, search_sims=5000)
req_port_s1 = result_s1['required_portfolio']
r_ret_s1 = find_required_contribution(
    initial_portfolio=initial_savings, target_portfolio=req_port_s1,
    stock_allocation=stock_alloc, stock_return=stock_return, stock_std=stock_std,
    bond_return=bond_return, bond_std=bond_std,
    current_age=current_age, retirement_age=retire_age_1,
    target_success_rate=success_rate, num_simulations=5000, seed=42,
)
pmt_ret_s1 = r_ret_s1['required_monthly_contribution'] / 1e6
prob_s1 = r_ret_s1['success_rate']
total_s1 = pmt_house_s1/1e6 + pmt_ret_s1

print('SCENARIO 1: Both at 50')
print('  House monthly: Rp' + str(round(pmt_house_s1/1e6, 2)) + 'M')
print('  Retirement monthly: Rp' + str(round(pmt_ret_s1, 2)) + 'M')
print('  Total (age 22-50): Rp' + str(round(total_s1, 2)) + 'M')
print('  Portfolio needed: Rp' + str(round(req_port_s1/1e9, 1)) + 'B')
print('  Success rate: ' + str(round(prob_s1, 1)) + '%')
print('  Spending at 50: Rp' + str(round(spending_at_50/1e6, 1)) + 'M/mo')
print()

# SCENARIO 2: Retire at 40, house at 50
retire_age_2 = 40
house_age_2 = 50
retire_years_2 = retire_age_2 - current_age
house_years_2 = house_age_2 - current_age

pmt_house_s2 = house_price * r_house / ((1 + r_house)**(house_years_2 * 12) - 1)
spending_at_40 = spending_today * (1 + inflation)**retire_years_2

inputs_s2 = SimulationInputs(
    initial_portfolio=10_000_000_000, monthly_spending=spending_at_40,
    inflation=inflation, stock_allocation=stock_alloc,
    stock_return=stock_return, stock_std=stock_std,
    bond_return=bond_return, bond_std=bond_std,
    retirement_age=retire_age_2, death_age=85,
    num_simulations=5000, seed=42,
)
result_s2 = find_required_portfolio(inputs_s2, target_success_rate=success_rate, search_sims=5000)
req_port_s2 = result_s2['required_portfolio']
r_ret_s2 = find_required_contribution(
    initial_portfolio=initial_savings, target_portfolio=req_port_s2,
    stock_allocation=stock_alloc, stock_return=stock_return, stock_std=stock_std,
    bond_return=bond_return, bond_std=bond_std,
    current_age=current_age, retirement_age=retire_age_2,
    target_success_rate=success_rate, num_simulations=5000, seed=42,
)
pmt_ret_s2 = r_ret_s2['required_monthly_contribution'] / 1e6
prob_s2 = r_ret_s2['success_rate']
total_22_40_s2 = pmt_ret_s2 + pmt_house_s2/1e6
total_40_50_s2 = pmt_house_s2/1e6

print('SCENARIO 2: Retire 40, House 50')
print('  House monthly: Rp' + str(round(pmt_house_s2/1e6, 2)) + 'M')
print('  Retirement monthly: Rp' + str(round(pmt_ret_s2, 2)) + 'M')
print('  Total (age 22-40): Rp' + str(round(total_22_40_s2, 2)) + 'M')
print('  Total (age 40-50): Rp' + str(round(total_40_50_s2, 2)) + 'M')
print('  Portfolio needed: Rp' + str(round(req_port_s2/1e9, 1)) + 'B')
print('  Success rate: ' + str(round(prob_s2, 1)) + '%')
print('  Spending at 40: Rp' + str(round(spending_at_40/1e6, 1)) + 'M/mo')
print()
# SCENARIO 3: Retire at 50, buy house at 40
retire_age_3 = 50
house_age_3 = 40
house_years_3 = house_age_3 - current_age
retire_years_3 = retire_age_3 - current_age

pmt_house_s3 = house_price * r_house / ((1 + r_house)**(house_years_3 * 12) - 1)
spending_at_50_s3 = spending_today * (1 + inflation)**retire_years_3

inputs_s3 = SimulationInputs(
    initial_portfolio=10_000_000_000, monthly_spending=spending_at_50_s3,
    inflation=inflation, stock_allocation=stock_alloc,
    stock_return=stock_return, stock_std=stock_std,
    bond_return=bond_return, bond_std=bond_std,
    retirement_age=retire_age_3, death_age=85,
    num_simulations=5000, seed=42,
)
result_s3 = find_required_portfolio(inputs_s3, target_success_rate=success_rate, search_sims=5000)
req_port_s3 = result_s3['required_portfolio']
r_ret_s3 = find_required_contribution(
    initial_portfolio=initial_savings, target_portfolio=req_port_s3,
    stock_allocation=stock_alloc, stock_return=stock_return, stock_std=stock_std,
    bond_return=bond_return, bond_std=bond_std,
    current_age=current_age, retirement_age=retire_age_3,
    target_success_rate=success_rate, num_simulations=5000, seed=42,
)
pmt_ret_s3 = r_ret_s3['required_monthly_contribution'] / 1e6
prob_s3 = r_ret_s3['success_rate']
total_22_40_s3 = pmt_ret_s3 + pmt_house_s3/1e6
total_40_50_s3 = pmt_ret_s3

print('SCENARIO 3: Retire 50, House 40')
print('  House monthly: Rp' + str(round(pmt_house_s3/1e6, 2)) + 'M')
print('  Retirement monthly: Rp' + str(round(pmt_ret_s3, 2)) + 'M')
print('  Total (age 22-40): Rp' + str(round(total_22_40_s3, 2)) + 'M')
print('  Total (age 40-50): Rp' + str(round(total_40_50_s3, 2)) + 'M')
print('  Portfolio needed: Rp' + str(round(req_port_s3/1e9, 1)) + 'B')
print('  Success rate: ' + str(round(prob_s3, 1)) + '%')
print('  Spending at 50: Rp' + str(round(spending_at_50_s3/1e6, 1)) + 'M/mo')
print()
print('='*60)
print('COMPARISON')
print('='*60)
print(f'{"Metric":<30} | {"S1: Both50":>12} | {"S2: Ret40/H50":>14} | {"S3: Ret50/H40":>14}')
print('-'*80)
print(f'{"Monthly (age 22-40)":<30} | {"—":>12} | Rp{total_22_40_s2:>12.1f}M | Rp{total_22_40_s3:>12.1f}M')
print(f'{"Monthly (age 40-50)":<30} | Rp{total_s1:>12.1f}M | Rp{total_40_50_s2:>12.1f}M | Rp{total_40_50_s3:>12.1f}M')
print(f'{"House monthly save":<30} | Rp{pmt_house_s1/1e6:>12.2f}M | Rp{pmt_house_s2/1e6:>12.2f}M | Rp{pmt_house_s3/1e6:>12.2f}M')
print(f'{"Retirement monthly save":<30} | Rp{pmt_ret_s1:>12.2f}M | Rp{pmt_ret_s2:>12.2f}M | Rp{pmt_ret_s3:>12.2f}M')
print(f'{"Total retirement target":<30} | Rp{req_port_s1/1e9:>12.1f}B | Rp{req_port_s2/1e9:>12.1f}B | Rp{req_port_s3/1e9:>12.1f}B')
print(f'{"House cost":<30} | Rp{house_price/1e9:>12.0f}B | Rp{house_price/1e9:>12.0f}B | Rp{house_price/1e9:>12.0f}B')
print(f'{"Retire at":<30} | {retire_age_1:>12} | {retire_age_2:>14} | {retire_age_3:>14}')
print(f'{"House at":<30} | {house_age_1:>12} | {house_age_2:>14} | {house_age_3:>14}')
print(f'{"Success rate":<30} | {prob_s1:>11.1f}% | {prob_s2:>13.1f}% | {prob_s3:>13.1f}%')
