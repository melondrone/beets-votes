import requests

beets_contract = "0xf24bcf4d1e507740041c9cfd2dddb29585adce1e"
ring = "30" # 32k total
lqdr = "25" # 400 lqdr ~10600 @26.6
pool_id = "25" # 1% = 1k

def get_data():
  price_url = "https://api.coingecko.com/api/v3/simple/token_price/fantom?contract_addresses=%s&vs_currencies=usd" % beets_contract
  snapshot_url = 'https://hub.snapshot.org/graphql?'
  snapshot_query = '''{
    votes (
      first: 100000
      where: {
        proposal: "0x8f28b88f32c80b3212afb0e850c6230023284fa33ccc2c14690c20195a086cb7"
      }
    ) {
      id
      voter
      created
      choice
      space {
        id
      }
      vp
      vp_by_strategy
    }
  }'''
  snapshot_response = requests.post(snapshot_url, json={'query': snapshot_query})
  price_response = requests.get(price_url)
  votes = snapshot_response.json()["data"]["votes"]
  price = price_response.json()[beets_contract]["usd"]

  voters = []

  for vote in votes:
    voters.append(vote["voter"])

  data = {
    "params": {
        "addresses": voters,
        "network": "250",
        "snapshot": 29883003,
        "space": "beets.eth",
        "strategies": [
            {
                "name": "erc20-balance-of",
                "params": {
                    "address": "0xfcef8a994209d6916EB2C86cDD2AFD60Aa6F54b1",
                    "decimals": 18,
                    "symbol": "fBEETS"
                }
            },
            {
                "name": "masterchef-pool-balance",
                "params": {
                    "chefAddress": "0x8166994d9ebBe5829EC86Bd81258149B87faCfd3",
                    "decimals": 18,
                    "pid": "22",
                    "symbol": "fBEETS-STAKED",
                    "uniPairAddress": None,
                    "weight": 1,
                    "weightDecimals": 0
                }
            }
        ]
    }
  }
  scores_response = requests.post("https://score.snapshot.org/api/scores", json=data)
  scores = scores_response.json()["result"]["scores"]

  return scores, votes, price

def stats(pool_id, bribed):
  total_votes = 0
  votes_to_us = 0
  addresses_voted_for_us = {}
  scores, votes, price = get_data()

  for vote in votes:
    balance = scores[0][vote["voter"]] + scores[1][vote["voter"]]
    total_votes += balance
    totalWeight = 0.0
    for choice in vote["choice"]:
      totalWeight += vote["choice"][choice]
    
    if pool_id in vote["choice"].keys():
      exodWeight = vote["choice"][pool_id] / totalWeight
      votes_to_us += exodWeight * balance
      addresses_voted_for_us[vote["voter"]] = exodWeight * balance

  exod_bribed = round(votes_to_us / total_votes * 100, 2) * 1000
  bribed = exod_bribed if bribed == "" else float(bribed)

  return votes, price, total_votes, votes_to_us, addresses_voted_for_us, bribed

def print_stats(pool_id, bribed):
  votes, price, total_votes, votes_to_us, addresses_voted_for_us, bribed = stats(pool_id, bribed)

  blocks_per_second = 1.0 / 0.9
  blocks_for_two_weeks = blocks_per_second * 60 * 60 * 24 * 14
  beets_per_block = 4.5
  beets_up_for_grabs = beets_per_block * blocks_for_two_weeks * 0.3
  cost_per_vote = beets_up_for_grabs * price / total_votes
  our_beets = beets_up_for_grabs * (votes_to_us / total_votes)
  our_gains = our_beets * price
  cost_per_vote = bribed / votes_to_us

  print("Beets price: $%s" % price)
  print("Total Votes: %s" % len(votes))
  print("")
  print("Total Beets Voted: %s" % '{:,}'.format(int(total_votes)))
  print("Beets up for grabs: %s" % '{:,}'.format(int(beets_up_for_grabs)))
  print("Vote worth: $%s" % '{:,}'.format(round(cost_per_vote, 2)))
  print("")
  print("Total Votes to us: %s" % '{:,}'.format(int(votes_to_us)))
  print("Percent to us: %s" % str(round(votes_to_us / total_votes * 100, 2)))
  print("Our Potential Beets rewards: %s BEETS | $%s" % ('{:,}'.format(int(our_beets)), '{:,}'.format(int(our_gains))))
  print("")
  print("Bribed($): %s" % '{:,}'.format(round(bribed, 2)))
  print("Price per vote: $%s" % '{:,}'.format(round(cost_per_vote, 4)))
  print("Profit: $%s" % '{:,}'.format(int(our_gains - bribed)))
  print("\n")

def payout(pool_id, bribed):
  _, _, total_votes, votes_to_us, addresses_voted_for_us, bribed = stats(pool_id, bribed)

  total_payout = 0
  for address in addresses_voted_for_us:
    weight = addresses_voted_for_us[address] / votes_to_us
    payout = weight * bribed
    print("%s   - %s DAI" % (address, round(payout, 2)))
    total_payout += payout

  print("Total payout: %s" % total_payout)
  print("\n")

while True:
  print("1. Payout\n2. Stats\n3. Exit")
  step = input("Enter selection (1,2,3): ")
  if step == 3:
    quit()

  pool_id = raw_input("Enter pool ID (blank for exodia): ")
  bribed = raw_input("Enter bribed($) (blank for exodia): ")
  print("Calculating results...\n")

  pool_id = "26" if pool_id == "" else pool_id

  if step == 1:
    payout(str(pool_id), bribed)
  if step == 2:
    print_stats(str(pool_id), bribed)
