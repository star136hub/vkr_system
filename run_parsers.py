import asyncio
from parsers.afisha_parser import AsyncAfishaParser
from parsers.culture_parser import AsyncCultureParser
from parsers.mts_parser import MTSParser
import logging


async def run_async_parser(parser):
    async with parser:
        return await parser.parse_events()


def run_sync_parser(parser):
    return parser.parse_events()


async def main():
    parsers = [
        AsyncAfishaParser(),
        AsyncCultureParser(),
        MTSParser()
    ]

    results = await asyncio.gather(
        run_async_parser(parsers[0]),
        run_async_parser(parsers[1]),
        asyncio.get_event_loop().run_in_executor(None, run_sync_parser, parsers[2])
    )

    logging.info(f"Спаршено: Afisha={len(results[0])}, Culture={len(results[1])}, MTS={len(results[2])}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())