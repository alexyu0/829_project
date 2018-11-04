import sys

def scrape(csv_path):
    with open(csv_path) as f:
        for line in f.readlines():
            if "not captured" in line:
                print(line)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scrape_loss_stats.py <path to wireshark csv>")
        sys.exit(1)

    scrape(sys.argv[1])
