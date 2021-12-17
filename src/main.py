from __future__ import absolute_import
import asyncio
from ui import UI

async def main():
    ui = UI()
    await ui.run()

if __name__ == "__main__":
    asyncio.run(main())