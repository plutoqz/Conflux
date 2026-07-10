"""Paper ingestion command line utilities."""

from __future__ import annotations

import argparse
import json
import sys

from conflux.knowledge.paper_indexer import promote_inbox
from conflux.research_profile import ProfileValidationError, load_profile

from .arxiv_source import profile_arxiv_queries, search_arxiv
from .dedup import deduplicate_papers
from .filters import apply_negative_filters
from .fixtures import load_paper_fixture
from .pipeline import build_inbox_from_arxiv, build_inbox_from_fixture


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Conflux paper ingestion utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fixture_parser = subparsers.add_parser("load-fixture", help="Load and normalize an offline paper fixture")
    fixture_parser.add_argument("fixture", help="Path to a paper fixture JSON file")
    fixture_parser.add_argument("--json", action="store_true", help="Print full records as JSON")

    crawl_parser = subparsers.add_parser("crawl", help="Plan or run a paper source crawl")
    crawl_parser.add_argument("--profile", required=True, help="Path to a research profile YAML file")
    crawl_parser.add_argument("--source", choices=["arxiv"], default="arxiv", help="Paper source")
    crawl_parser.add_argument("--dry-run", action="store_true", help="Print planned queries without network access")
    crawl_parser.add_argument("--max-results", type=int, default=10, help="Maximum results for a real crawl")

    inbox_parser = subparsers.add_parser("inbox", help="Build a scored paper radar inbox")
    inbox_parser.add_argument("--profile", required=True, help="Path to a research profile YAML file")
    inbox_source = inbox_parser.add_mutually_exclusive_group(required=True)
    inbox_source.add_argument("--fixture", help="Path to an offline paper fixture JSON file")
    inbox_source.add_argument("--source", choices=["arxiv"], help="Real paper source")
    inbox_parser.add_argument("--out-dir", default="reports/papers", help="Directory for paper_inbox.md/json")
    inbox_parser.add_argument("--max-results", type=int, default=10, help="Maximum results for a real source")

    promote_parser = subparsers.add_parser("promote", help="Promote a paper inbox into reviewable RAG documents")
    promote_parser.add_argument("inbox", help="Path to paper_inbox.json")
    promote_parser.add_argument("--out-dir", default="data/documents/papers", help="Directory for promoted documents")
    promote_parser.add_argument("--policy", default="default", help="Promotion policy name")
    promote_parser.add_argument("--full-text", action="store_true", help="Enable full-text decisions when PDFs are available")
    promote_parser.add_argument("--pdf-dir", help="Directory containing cached PDFs or receiving downloads")
    promote_parser.add_argument("--download-pdfs", action="store_true", help="Download PDFs for full-text promotion")
    promote_parser.add_argument("--pin", action="append", default=[], help="Paper ID to force include; may be repeated")
    promote_parser.add_argument("--index", action="store_true", help="Write promoted documents to the configured Chroma index")

    args = parser.parse_args(argv)

    try:
        if args.command == "load-fixture":
            papers = deduplicate_papers(load_paper_fixture(args.fixture))
            if args.json:
                print(json.dumps([paper.to_dict() for paper in papers], ensure_ascii=False, indent=2))
            else:
                print(f"Loaded {len(papers)} unique papers from {args.fixture}")
                for paper in papers:
                    print(f"- {paper.id}: {paper.title}")
            return 0

        if args.command == "crawl":
            profile = load_profile(args.profile)
            queries = profile_arxiv_queries(profile)
            if args.dry_run:
                print(json.dumps({
                    "source": args.source,
                    "profile_id": profile.id,
                    "queries": queries,
                }, ensure_ascii=False, indent=2))
                return 0

            papers = []
            for query in queries:
                papers.extend(search_arxiv(query, max_results=args.max_results))
            papers = apply_negative_filters(deduplicate_papers(papers), profile)
            print(json.dumps([paper.to_dict() for paper in papers], ensure_ascii=False, indent=2))
            return 0

        if args.command == "inbox":
            if args.fixture:
                result = build_inbox_from_fixture(args.profile, args.fixture, out_dir=args.out_dir)
            else:
                result = build_inbox_from_arxiv(args.profile, max_results=args.max_results, out_dir=args.out_dir)
            artifacts = result.artifacts
            print(f"Paper inbox built for profile: {result.profile.id}")
            print(f"Total loaded: {result.stats['total_loaded']}")
            print(f"After deduplication: {result.stats['after_dedup']}")
            print(f"After negative filters: {result.stats['after_filter']}")
            print(f"Deep/skim/skip: {result.stats['deep']}/{result.stats['skim']}/{result.stats['skip']}")
            if artifacts:
                print(f"Markdown inbox: {artifacts.markdown_path.resolve()}")
                print(f"JSON inbox: {artifacts.json_path.resolve()}")
            return 0

        if args.command == "promote":
            result = promote_inbox(
                args.inbox,
                out_dir=args.out_dir,
                policy_name=args.policy,
                allow_full_text=args.full_text,
                pinned_ids=args.pin,
                index=args.index,
                pdf_dir=args.pdf_dir,
                download_pdfs=args.download_pdfs,
            )
            actions = {}
            for decision in result.decisions:
                actions[decision.action] = actions.get(decision.action, 0) + 1
            print(f"Paper inbox promoted: {args.inbox}")
            print(f"Promoted documents: {len(result.documents)}")
            print(f"Indexed documents: {result.indexed_count}")
            print(f"Decision counts: {json.dumps(actions, ensure_ascii=False, sort_keys=True)}")
            if result.artifacts:
                print(f"Documents directory: {result.artifacts.documents_dir.resolve()}")
                print(f"Promotion manifest: {result.artifacts.manifest_path.resolve()}")
                print(f"Knowledge sources: {result.artifacts.sources_path.resolve()}")
            return 0

    except (OSError, ValueError, ProfileValidationError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
