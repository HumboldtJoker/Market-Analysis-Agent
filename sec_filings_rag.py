"""
SEC Filings RAG Module for AutoInvestor

Retrieval-Augmented Generation for SEC filings (10-K, 10-Q, 8-K).
Enables natural language queries against company financial disclosures.

Data Source: SEC EDGAR (Electronic Data Gathering, Analysis, and Retrieval)
- Free public API, no authentication required
- Rate limit: 10 requests per second (we'll be conservative)

Filing Types:
- 10-K: Annual report (comprehensive financials, risks, strategy)
- 10-Q: Quarterly report (interim financials)
- 8-K: Current report (material events - acquisitions, leadership changes, etc.)

Author: Lyra & Thomas (Coalition)
Version: 1.0.0 - 2025-11-25
"""

import os
import re
import json
import time
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import hashlib

# Optional imports for RAG functionality
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


# SEC EDGAR API configuration
SEC_EDGAR_SUBMISSIONS = "https://data.sec.gov/submissions"
SEC_EDGAR_FILINGS = "https://www.sec.gov/Archives/edgar/data"

# User agent required by SEC (they block requests without proper identification)
# SEC requires a valid email in user agent
SEC_USER_AGENT = "AutoInvestor/1.0 (Coalition Research; thomas@coalition.ai)"

# Rate limiting
RATE_LIMIT_DELAY = 0.15  # 150ms between requests (conservative)


class SECFilingsRAG:
    """
    RAG system for SEC filings

    Fetches, processes, and enables semantic search over SEC filings.
    """

    def __init__(self, cache_dir: str = None, embedding_model: str = "all-MiniLM-L6-v2"):
        """
        Initialize SEC Filings RAG

        Args:
            cache_dir: Directory to cache downloaded filings
            embedding_model: Sentence transformer model for embeddings
        """
        self.cache_dir = Path(cache_dir or os.path.join(
            os.path.dirname(__file__), ".sec_cache"
        ))
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize embedding model if available
        self.embedding_model = None
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer(embedding_model)
            except Exception as e:
                print(f"Warning: Could not load embedding model: {e}")

        # Initialize ChromaDB if available
        self.chroma_client = None
        self.collection = None
        if CHROMADB_AVAILABLE:
            try:
                # Use new ChromaDB API
                persist_path = str(self.cache_dir / "chroma_db")
                self.chroma_client = chromadb.PersistentClient(path=persist_path)
                self.collection = self.chroma_client.get_or_create_collection(
                    name="sec_filings",
                    metadata={"description": "SEC filings for AutoInvestor"}
                )
            except Exception as e:
                # Fallback to ephemeral client
                try:
                    self.chroma_client = chromadb.Client()
                    self.collection = self.chroma_client.get_or_create_collection(
                        name="sec_filings"
                    )
                except Exception as e2:
                    print(f"Warning: Could not initialize ChromaDB: {e2}")

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": SEC_USER_AGENT})

    def get_company_cik(self, ticker: str) -> Optional[str]:
        """
        Get CIK (Central Index Key) for a company by ticker

        Args:
            ticker: Stock ticker symbol

        Returns:
            CIK number or None if not found
        """
        ticker = ticker.upper().strip()

        # Check cache first
        cik_cache_file = self.cache_dir / "cik_lookup.json"
        cik_cache = {}
        if cik_cache_file.exists():
            try:
                cik_cache = json.loads(cik_cache_file.read_text())
                if ticker in cik_cache:
                    return cik_cache[ticker]
            except:
                pass

        try:
            # Fetch company tickers JSON from SEC
            time.sleep(RATE_LIMIT_DELAY)
            url = "https://www.sec.gov/files/company_tickers.json"
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            data = response.json()

            # Search for ticker
            for entry in data.values():
                if entry.get('ticker', '').upper() == ticker:
                    cik = str(entry['cik_str']).zfill(10)
                    # Cache the result
                    cik_cache[ticker] = cik
                    cik_cache_file.write_text(json.dumps(cik_cache))
                    return cik

            return None

        except Exception as e:
            print(f"Error looking up CIK for {ticker}: {e}")
            return None

    def get_recent_filings(self, ticker: str, filing_types: List[str] = None,
                          count: int = 10) -> List[Dict]:
        """
        Get recent SEC filings for a company

        Args:
            ticker: Stock ticker symbol
            filing_types: List of filing types (default: ['10-K', '10-Q', '8-K'])
            count: Maximum number of filings to return

        Returns:
            List of filing metadata dicts
        """
        if filing_types is None:
            filing_types = ['10-K', '10-Q', '8-K']

        cik = self.get_company_cik(ticker)
        if not cik:
            return []

        try:
            # Fetch submissions for company
            time.sleep(RATE_LIMIT_DELAY)
            url = f"{SEC_EDGAR_SUBMISSIONS}/CIK{cik}.json"
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            data = response.json()
            recent_filings = data.get('filings', {}).get('recent', {})

            # Extract filing information
            filings = []
            forms = recent_filings.get('form', [])
            dates = recent_filings.get('filingDate', [])
            accessions = recent_filings.get('accessionNumber', [])
            primary_docs = recent_filings.get('primaryDocument', [])

            for i, form in enumerate(forms):
                if form in filing_types:
                    filings.append({
                        'ticker': ticker,
                        'cik': cik,
                        'form': form,
                        'filing_date': dates[i] if i < len(dates) else None,
                        'accession_number': accessions[i] if i < len(accessions) else None,
                        'primary_document': primary_docs[i] if i < len(primary_docs) else None,
                    })

                    if len(filings) >= count:
                        break

            return filings

        except Exception as e:
            print(f"Error fetching filings for {ticker}: {e}")
            return []

    def download_filing(self, filing: Dict) -> Optional[str]:
        """
        Download and extract text from a filing

        Args:
            filing: Filing metadata dict from get_recent_filings

        Returns:
            Extracted text content or None
        """
        cik = filing['cik'].lstrip('0')  # Remove leading zeros for URL
        accession = filing['accession_number'].replace('-', '')
        primary_doc = filing['primary_document']

        # Check cache
        cache_key = hashlib.md5(f"{cik}_{accession}_{primary_doc}".encode()).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.txt"

        if cache_file.exists():
            return cache_file.read_text(encoding='utf-8', errors='ignore')

        try:
            # Construct filing URL
            time.sleep(RATE_LIMIT_DELAY)
            url = f"{SEC_EDGAR_FILINGS}/{cik}/{accession}/{primary_doc}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            content = response.text

            # Clean HTML if present
            if '<html' in content.lower() or '<body' in content.lower():
                content = self._clean_html(content)

            # Cache the result
            cache_file.write_text(content, encoding='utf-8')

            return content

        except Exception as e:
            print(f"Error downloading filing: {e}")
            return None

    def _clean_html(self, html_content: str) -> str:
        """
        Extract text from HTML filing

        Args:
            html_content: Raw HTML content

        Returns:
            Cleaned text
        """
        # Remove script and style elements
        text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)

        # Decode HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')

        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = '\n'.join(line.strip() for line in text.split('\n') if line.strip())

        return text

    def chunk_filing(self, text: str, chunk_size: int = 1000,
                    overlap: int = 200) -> List[str]:
        """
        Split filing text into chunks for embedding

        Args:
            text: Full filing text
            chunk_size: Target chunk size in characters
            overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        if not text:
            return []

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for period followed by space or newline
                break_point = text.rfind('. ', start + chunk_size // 2, end + 100)
                if break_point > start:
                    end = break_point + 1

            chunks.append(text[start:end].strip())
            start = end - overlap

        return chunks

    def index_filing(self, ticker: str, filing: Dict) -> int:
        """
        Download, chunk, and index a filing into the vector store

        Args:
            ticker: Stock ticker
            filing: Filing metadata dict

        Returns:
            Number of chunks indexed
        """
        if not self.collection:
            print("Warning: ChromaDB not available, skipping indexing")
            return 0

        # Download filing
        content = self.download_filing(filing)
        if not content:
            return 0

        # Chunk the content
        chunks = self.chunk_filing(content)
        if not chunks:
            return 0

        # Generate IDs and metadata
        filing_id = f"{ticker}_{filing['form']}_{filing['filing_date']}"

        ids = [f"{filing_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{
            'ticker': ticker,
            'form': filing['form'],
            'filing_date': filing['filing_date'],
            'chunk_index': i,
            'total_chunks': len(chunks)
        } for i in range(len(chunks))]

        # Add to collection
        try:
            self.collection.add(
                documents=chunks,
                ids=ids,
                metadatas=metadatas
            )
            return len(chunks)
        except Exception as e:
            print(f"Error indexing filing: {e}")
            return 0

    def search(self, query: str, ticker: str = None, filing_type: str = None,
              n_results: int = 5) -> List[Dict]:
        """
        Semantic search over indexed filings

        Args:
            query: Natural language query
            ticker: Optional ticker to filter results
            filing_type: Optional filing type to filter (10-K, 10-Q, 8-K)
            n_results: Number of results to return

        Returns:
            List of search results with text and metadata
        """
        if not self.collection:
            return [{'error': 'ChromaDB not available. Install with: pip install chromadb'}]

        # Build filter
        where_filter = {}
        if ticker:
            where_filter['ticker'] = ticker.upper()
        if filing_type:
            where_filter['form'] = filing_type

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter if where_filter else None
            )

            # Format results
            formatted = []
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                distance = results['distances'][0][i] if results.get('distances') else None

                formatted.append({
                    'text': doc,
                    'ticker': metadata.get('ticker'),
                    'form': metadata.get('form'),
                    'filing_date': metadata.get('filing_date'),
                    'relevance_score': 1 - distance if distance else None
                })

            return formatted

        except Exception as e:
            return [{'error': f'Search failed: {str(e)}'}]

    def get_filing_summary(self, ticker: str, filing_type: str = '10-K') -> Dict:
        """
        Get a summary of a company's most recent filing

        Args:
            ticker: Stock ticker symbol
            filing_type: Type of filing (default: 10-K)

        Returns:
            Dict with filing info and key sections
        """
        filings = self.get_recent_filings(ticker, [filing_type], count=1)

        if not filings:
            return {'error': f'No {filing_type} filings found for {ticker}'}

        filing = filings[0]
        content = self.download_filing(filing)

        if not content:
            return {'error': 'Could not download filing'}

        # Extract key sections (simplified - real implementation would use XBRL)
        sections = {}

        # Look for common section headers
        section_patterns = [
            (r'ITEM\s*1[.\s]+BUSINESS', 'business_description'),
            (r'ITEM\s*1A[.\s]+RISK\s*FACTORS', 'risk_factors'),
            (r'ITEM\s*7[.\s]+MANAGEMENT', 'management_discussion'),
            (r'ITEM\s*8[.\s]+FINANCIAL\s*STATEMENTS', 'financial_statements'),
        ]

        content_upper = content.upper()
        for pattern, section_name in section_patterns:
            match = re.search(pattern, content_upper)
            if match:
                # Get a snippet after the header
                start = match.end()
                end = min(start + 2000, len(content))
                sections[section_name] = content[start:end].strip()[:500] + "..."

        return {
            'ticker': ticker,
            'filing_type': filing_type,
            'filing_date': filing['filing_date'],
            'accession_number': filing['accession_number'],
            'sections_found': list(sections.keys()),
            'section_previews': sections,
            'full_text_length': len(content),
            'verification_url': f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type={filing_type}"
        }


def analyze_sec_filings(ticker: str, query: str = None,
                       filing_types: List[str] = None) -> Dict:
    """
    Main interface for SEC filings analysis

    Args:
        ticker: Stock ticker symbol
        query: Optional natural language query to search filings
        filing_types: Types of filings to analyze (default: ['10-K', '10-Q'])

    Returns:
        Analysis results dict
    """
    if filing_types is None:
        filing_types = ['10-K', '10-Q']

    rag = SECFilingsRAG()

    # Get recent filings
    filings = rag.get_recent_filings(ticker, filing_types, count=5)

    if not filings:
        return {
            'error': f'No SEC filings found for {ticker}',
            'suggestion': 'Verify the ticker symbol is correct and the company files with SEC'
        }

    # Get summary of most recent 10-K if available
    summary = None
    if '10-K' in filing_types:
        summary = rag.get_filing_summary(ticker, '10-K')

    # If query provided and RAG is available, search
    search_results = None
    if query and CHROMADB_AVAILABLE:
        # Index recent filings first
        for filing in filings[:3]:  # Index top 3
            rag.index_filing(ticker, filing)

        search_results = rag.search(query, ticker=ticker, n_results=3)

    # Format output
    analysis_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')

    output = f"""
SEC FILINGS ANALYSIS FOR {ticker.upper()}
Analysis Timestamp: {analysis_time}

DATA SOURCE:
SEC EDGAR (Electronic Data Gathering, Analysis, and Retrieval)
Verification: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}

RECENT FILINGS:
"""

    for f in filings:
        output += f"  - {f['form']}: Filed {f['filing_date']}\n"

    if summary and 'error' not in summary:
        output += f"""
LATEST 10-K SUMMARY:
Filing Date: {summary['filing_date']}
Full Text Length: {summary['full_text_length']:,} characters
Sections Found: {', '.join(summary['sections_found'])}
"""
        if summary.get('section_previews', {}).get('risk_factors'):
            output += f"""
RISK FACTORS PREVIEW:
{summary['section_previews']['risk_factors'][:500]}...
"""

    if search_results and not any('error' in r for r in search_results):
        output += f"""
SEARCH RESULTS FOR: "{query}"
"""
        for i, result in enumerate(search_results, 1):
            output += f"""
Result {i} (Relevance: {result.get('relevance_score', 'N/A'):.2f}):
Source: {result.get('form')} filed {result.get('filing_date')}
Text: {result['text'][:300]}...
"""

    output += """
IMPORTANT DISCLAIMER:
SEC filings are official company disclosures but may be outdated.
Always verify information at sec.gov. This analysis extracts text
from filings but does not constitute financial advice.
"""

    return {
        'summary': output.strip(),
        'raw_data': {
            'ticker': ticker,
            'filings': filings,
            'latest_summary': summary,
            'search_results': search_results
        },
        'analysis_timestamp': analysis_time
    }


if __name__ == "__main__":
    import sys

    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    query = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"\nAnalyzing SEC filings for {ticker}...")
    if query:
        print(f"Query: {query}\n")

    result = analyze_sec_filings(ticker, query)

    if "error" in result:
        print(f"ERROR: {result['error']}")
    else:
        print(result['summary'])
