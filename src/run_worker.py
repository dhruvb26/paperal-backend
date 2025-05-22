from hatchet_sdk import Hatchet
from api.hatchet_task import process_urls_task

def main() -> None:
  hatchet = Hatchet(debug=True)
  worker = hatchet.worker("paperal-worker", workflows=[process_urls_task])
  worker.start()
 
if __name__ == "__main__":
    main()