import argparse
import asyncio
import os
import sys
from typing import Optional

from .core_engine import CoreEngine, SearchOptions
from .storage.dal_factory import get_dal_instance
from .logger_config import setup_logging

logger = setup_logging()

async def search_command(args, engine: CoreEngine):
    """Execute search command."""
    options = SearchOptions(
        rerank=not args.no_rerank,
        top_k=args.max_count,
        include_web=args.web,
        content=args.content,
        use_zoekt=True # Always try to use Zoekt if available for CLI
    )

    # Check if path is provided, otherwise use current directory
    search_path = args.path if args.path else os.getcwd()
    search_path = os.path.abspath(search_path)

    store_ids = [search_path]

    if args.answer:
        # Ask mode (RAG)
        response = await engine.ask(store_ids, args.pattern, options)
        print(f"\nAnswer:\n{response.answer}\n")
        print("Sources:")
        for source in response.sources:
            path = source.metadata.path if source.metadata else "Unknown"
            print(f"- {path} (Score: {source.score:.2f})")
    else:
        # Search mode
        response = await engine.search(store_ids, args.pattern, options)
        if not response.data:
            print("No results found.")
            return

        for item in response.data:
            path = item.metadata.path if item.metadata else "Unknown"
            if item.filename: # Web result
                path = item.filename

            line_info = ""
            if item.generated_metadata and "line_number" in item.generated_metadata:
                line_info = f":{item.generated_metadata['line_number']}"

            print(f"{path}{line_info} (Score: {item.score:.2f})")
            if args.content and item.text:
                print(f"  {item.text.strip()}")
            print()

async def stats_command(args):
    """
    Execute stats command.

    PRODUCT.MD ALIGNMENT:
    ---------------------
    "Index Statistics Dashboard: CLI command showing index health metrics"

    Shows index health, document counts, and backend status.
    """
    from .stats_dashboard import IndexStatisticsCollector, DashboardCLI

    es_url = args.es_url or os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
    pg_dsn = args.pg_dsn or os.getenv("DATABASE_URL")

    collector = IndexStatisticsCollector(
        pg_dsn=pg_dsn,
        es_url=es_url,
    )

    cli = DashboardCLI(collector)

    if args.json:
        await cli.show_json()
    else:
        await cli.show_stats(watch=args.watch, interval=args.interval)

def main():
    parser = argparse.ArgumentParser(description="Code Search CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Search command (default for backward compatibility)
    search_parser = subparsers.add_parser("search", help="Search code", add_help=False)
    search_parser.add_argument("pattern", help="The pattern or question to search for")
    search_parser.add_argument("path", nargs="?", help="The path to search in (default: current directory)")
    search_parser.add_argument("-w", "--web", action="store_true", help="Include web search results")
    search_parser.add_argument("-a", "--answer", action="store_true", help="Generate an answer (RAG mode)")
    search_parser.add_argument("-c", "--content", action="store_true", help="Show content of results")
    search_parser.add_argument("-m", "--max-count", type=int, default=10, help="Maximum number of results")
    search_parser.add_argument("--no-rerank", action="store_true", help="Disable reranking")

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show index statistics")
    stats_parser.add_argument("--es-url", help="Elasticsearch URL")
    stats_parser.add_argument("--pg-dsn", help="PostgreSQL connection string")
    stats_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    stats_parser.add_argument("--watch", action="store_true", help="Continuously update")
    stats_parser.add_argument("--interval", type=int, default=5, help="Update interval for watch mode")

    # Default to search if no command specified (backward compatibility)
    args = parser.parse_args()

    if args.command == "stats":
        # Stats command
        asyncio.run(stats_command(args))
    else:
        # Default to search for backward compatibility
        # If no subcommand was used, treat positional args as search args
        if args.command is None:
            # Re-parse with search-only behavior
            parser = argparse.ArgumentParser(description="Code Search CLI")
            parser.add_argument("pattern", help="The pattern or question to search for")
            parser.add_argument("path", nargs="?", help="The path to search in (default: current directory)")
            parser.add_argument("-w", "--web", action="store_true", help="Include web search results")
            parser.add_argument("-a", "--answer", action="store_true", help="Generate an answer (RAG mode)")
            parser.add_argument("-c", "--content", action="store_true", help="Show content of results")
            parser.add_argument("-m", "--max-count", type=int, default=10, help="Maximum number of results")
            parser.add_argument("--no-rerank", action="store_true", help="Disable reranking")
            args = parser.parse_args()

        # Initialize components
        try:
            # We need a DAL instance for legacy fallback
            # Use simple sqlite config if env vars not set, to avoid crashing CLI if not fully configured
            try:
                dal_instance = get_dal_instance()
            except Exception as e:
                logger.warning(f"Could not initialize full DAL: {e}. Falling back to minimal configuration.")
                dal_instance = None

            engine = CoreEngine(legacy_backend=dal_instance)

            # Run async command
            asyncio.run(search_command(args, engine))

        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            sys.exit(130)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
