"""
Conflux RAG Corpus Downloader
==============================
Downloads documents from multiple sources for the RAG knowledge base.
Supports: Esri docs, open-source QA datasets, NIST pubs, Wikipedia, and more.

Usage:
    python scripts/download_corpus.py [--targets esri,qa,nist,wiki,all]
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ── Config ──────────────────────────────────────────────────────────
OUTPUT_DIR = Path("data/documents")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
}

REQUEST_TIMEOUT = 30
DELAY_BETWEEN_REQUESTS = 0.5  # seconds, be polite


# ══════════════════════════════════════════════════════════════════════
# Utility Functions
# ══════════════════════════════════════════════════════════════════════

def safe_filename(name: str, max_len: int = 80) -> str:
    """Sanitise a string into a safe filename."""
    name = re.sub(r"[\\/:*?\"<>|]+", "_", name)
    name = re.sub(r"\s+", "-", name)
    name = name.strip("-_.")
    return name[:max_len]


def save_document(filename: str, content: str, source_url: str = ""):
    """Save content as .md with metadata header."""
    path = OUTPUT_DIR / filename
    lines = []
    if source_url:
        lines.append(f"<!-- source: {source_url} -->")
    lines.append(content)
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  [OK] {filename}  ({len(content)} chars)")
    return path


def fetch_url(url: str) -> str | None:
    """Fetch a URL and return text content."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    except Exception as e:
        print(f"  [FAIL] Failed: {url} — {e}")
        return None


def html_to_markdown_text(html: str, url: str = "") -> str:
    """Rudimentary HTML→text converter for documentation pages."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove scripts, styles, nav, footer
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    # Try to find main content area
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find("div", class_="content")
        or soup.find("div", id="content")
        or soup.find("div", id="mw-content-text")
        or soup.find("div", class_="mw-parser-output")
        or soup.body
    )
    if main is None and soup.find():
        # Fallback: use the first top-level element (e.g. for HTML fragments)
        main = soup.find() if soup.find() else soup
    if main is None:
        return ""

    lines = []
    for el in main.descendants:
        if el.name is None:
            text = str(el).strip()
            if text:
                lines.append(text)
        elif el.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(el.name[1])
            text = el.get_text(strip=True)
            if text:
                lines.append(f"\n{'#' * level} {text}\n")
        elif el.name == "p":
            text = el.get_text(strip=True)
            if text and len(text) > 20:
                lines.append(text + "\n")
        elif el.name == "li":
            text = el.get_text(strip=True)
            if text:
                lines.append(f"- {text}")
        elif el.name in ("pre", "code"):
            text = el.get_text()
            if text.strip():
                lines.append(f"\n```\n{text.strip()}\n```\n")
        elif el.name == "table":
            lines.append("\n<!-- table omitted -->\n")

    result = "\n".join(lines)
    # Collapse excessive blank lines
    result = re.sub(r"\n{4,}", "\n\n\n", result)
    return result.strip()


# ══════════════════════════════════════════════════════════════════════
# 1. Esri Documentation
# ══════════════════════════════════════════════════════════════════════

ESRI_URLS = {
    # ArcGIS Pro — core concepts
    "arcgis-pro-welcome": "https://pro.arcgis.com/en/pro-app/latest/help/main/welcome-to-the-arcgis-pro-app-help.htm",
    "arcgis-pro-get-started": "https://pro.arcgis.com/en/pro-app/latest/get-started/get-started.htm",
    "arcgis-pro-projects": "https://pro.arcgis.com/en/pro-app/latest/help/projects/arcgis-pro-projects.htm",
    "arcgis-pro-maps": "https://pro.arcgis.com/en/pro-app/latest/help/mapping/mapping.htm",
    "arcgis-pro-layers": "https://pro.arcgis.com/en/pro-app/latest/help/mapping/layer-properties/layers.htm",
    "arcgis-pro-analysis": "https://pro.arcgis.com/en/pro-app/latest/help/analysis/geoprocessing/basics/what-is-geoprocessing-.htm",
    "arcgis-pro-geodatabase": "https://pro.arcgis.com/en/pro-app/latest/help/data/geodatabases/overview/what-is-a-geodatabase-.htm",
    "arcgis-pro-editing": "https://pro.arcgis.com/en/pro-app/latest/help/editing/editing.htm",
    "arcgis-pro-share": "https://pro.arcgis.com/en/pro-app/latest/help/sharing/overview/sharing.htm",
    "arcgis-pro-symbology": "https://pro.arcgis.com/en/pro-app/latest/help/mapping/symbols-and-styles/symbols-and-styles.htm",
    "arcgis-pro-labels": "https://pro.arcgis.com/en/pro-app/latest/help/mapping/text/labeling.htm",
    "arcgis-pro-3d": "https://pro.arcgis.com/en/pro-app/latest/help/mapping/3d/3d.htm",
    "arcgis-pro-layouts": "https://pro.arcgis.com/en/pro-app/latest/help/layouts/layouts.htm",
    "arcgis-pro-tasks": "https://pro.arcgis.com/en/pro-app/latest/help/tasks/tasks.htm",
    "arcgis-pro-modelbuilder": "https://pro.arcgis.com/en/pro-app/latest/help/analysis/geoprocessing/modelbuilder/what-is-modelbuilder-.htm",
    "arcgis-pro-python": "https://pro.arcgis.com/en/pro-app/latest/arcpy/get-started/arcgis-pro-and-arcpy.htm",
    "arcgis-pro-spatial-reference": "https://pro.arcgis.com/en/pro-app/latest/help/mapping/properties/coordinate-systems-and-projections.htm",

    # ArcGIS Enterprise
    "arcgis-enterprise-overview": "https://enterprise.arcgis.com/en/get-started/latest/windows/what-is-arcgis-enterprise-.htm",
    "arcgis-enterprise-components": "https://enterprise.arcgis.com/en/get-started/latest/windows/components-of-arcgis-enterprise.htm",
    "arcgis-enterprise-deploy": "https://enterprise.arcgis.com/en/get-started/latest/windows/deployment-overview.htm",
    "arcgis-enterprise-portal": "https://enterprise.arcgis.com/en/portal/latest/administer/windows/what-is-portal-for-arcgis-.htm",
    "arcgis-enterprise-server": "https://enterprise.arcgis.com/en/server/latest/administer/windows/what-is-arcgis-server-.htm",
    "arcgis-enterprise-datastore": "https://enterprise.arcgis.com/en/portal/latest/administer/windows/what-is-arcgis-data-store-.htm",
    "arcgis-enterprise-federate": "https://enterprise.arcgis.com/en/server/latest/administer/windows/federate-an-arcgis-server-site-with-your-portal.htm",

    # ArcGIS REST API
    "arcgis-rest-api-overview": "https://developers.arcgis.com/rest/services-reference/enterprise/what-s-new-in-the-arcgis-rest-api-.htm",
    "arcgis-rest-api-services": "https://developers.arcgis.com/rest/services-reference/enterprise/services-reference.htm",
    "arcgis-rest-api-feature": "https://developers.arcgis.com/rest/services-reference/enterprise/feature-service.htm",
    "arcgis-rest-api-map": "https://developers.arcgis.com/rest/services-reference/enterprise/map-service.htm",
    "arcgis-rest-api-geocode": "https://developers.arcgis.com/rest/services-reference/enterprise/geocode-service.htm",

    # ArcGIS Python API
    "arcgis-python-api-overview": "https://developers.arcgis.com/python/latest/guide/overview-of-the-arcgis-api-for-python/",
    "arcgis-python-api-gis": "https://developers.arcgis.com/python/latest/guide/the-gis-module/",
    "arcgis-python-api-mapping": "https://developers.arcgis.com/python/latest/guide/mapping-module/",
    "arcgis-python-api-analysis": "https://developers.arcgis.com/python/latest/guide/geoanalytics-module/",
    "arcgis-python-api-geocoding": "https://developers.arcgis.com/python/latest/guide/geocoding/",

    # ArcGIS Online
    "arcgis-online-overview": "https://doc.arcgis.com/en/arcgis-online/get-started/what-is-agol.htm",
    "arcgis-online-maps": "https://doc.arcgis.com/en/arcgis-online/get-started/get-started-with-maps.htm",
    "arcgis-online-scenes": "https://doc.arcgis.com/en/arcgis-online/get-started/get-started-with-scenes.htm",
    "arcgis-online-apps": "https://doc.arcgis.com/en/arcgis-online/get-started/get-started-with-apps.htm",

    # Spatial Analysis / GeoAnalytics
    "arcgis-spatial-analysis": "https://pro.arcgis.com/en/pro-app/latest/tool-reference/spatial-analyst/an-overview-of-the-spatial-analyst-toolbox.htm",
    "arcgis-geostatistics": "https://pro.arcgis.com/en/pro-app/latest/tool-reference/geostatistical-analyst/an-overview-of-the-geostatistical-analyst-toolbox.htm",
    "arcgis-network-analyst": "https://pro.arcgis.com/en/pro-app/latest/tool-reference/network-analyst/an-overview-of-the-network-analyst-toolbox.htm",
}


def download_esri_docs():
    """Download Esri documentation pages."""
    print("\n" + "=" * 60)
    print("  1. Downloading Esri Documentation")
    print("=" * 60)

    success_count = 0
    for slug, url in ESRI_URLS.items():
        print(f"\n  [{slug}]")
        html = fetch_url(url)
        if not html:
            continue

        # Extract title
        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else slug.replace("-", " ").title()

        text = html_to_markdown_text(html, url)
        if not text or len(text) < 200:
            print(f"    [WARN] Too little content ({len(text)} chars), skipping")
            continue

        full_content = f"# {title}\n\n> Source: {url}\n\n{text}"
        filename = f"esri--{slug}.md"
        save_document(filename, full_content, url)
        success_count += 1
        time.sleep(DELAY_BETWEEN_REQUESTS)

    print(f"\n  [OK] Downloaded {success_count}/{len(ESRI_URLS)} Esri pages")
    return success_count


# ══════════════════════════════════════════════════════════════════════
# 2. Open-Source QA Datasets
# ══════════════════════════════════════════════════════════════════════

def download_squad_v2():
    """Download SQuAD v2.0 dataset via Hugging Face datasets library."""
    print("\n" + "=" * 60)
    print("  2a. Downloading SQuAD v2.0 Dataset")
    print("=" * 60)

    try:
        from datasets import load_dataset
    except ImportError:
        print("  [WARN] datasets library not installed. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "datasets", "-q"])
        from datasets import load_dataset

    try:
        print("  Loading SQuAD v2.0 from Hugging Face...")
        dataset = load_dataset("squad_v2", split="train", trust_remote_code=True)
        print(f"  Loaded {len(dataset)} examples")

        # Save as JSON for evaluation purposes
        json_path = OUTPUT_DIR / "squad-v2-train.json"
        # Take first 2000 examples to keep file manageable
        subset = dataset.select(range(min(2000, len(dataset))))
        subset.to_json(str(json_path))
        print(f"  [OK] squad-v2-train.json ({json_path.stat().st_size:,} bytes, {len(subset)} examples)")

        # Also save as readable .md for RAG
        md_lines = [
            "# SQuAD v2.0 — Stanford Question Answering Dataset (Sample)",
            "",
            f"> Total examples in sample: {len(subset)}",
            "> SQuAD v2.0 combines 100K answerable questions with 50K unanswerable ones.",
            "> Each unanswerable question must be answered with an empty string.",
            "",
            "---",
            "",
        ]
        for i, item in enumerate(subset):
            if i >= 500:  # Limit markdown to 500 Q&A pairs
                break
            context = item.get("context", "")
            question = item.get("question", "")
            answers = item.get("answers", {}).get("text", [])
            is_impossible = item.get("is_impossible", False)

            md_lines.append(f"## Q{i+1}: {question}")
            md_lines.append(f"")
            if is_impossible:
                md_lines.append(f"**Answer:** (unanswerable)")
            elif answers:
                md_lines.append(f"**Answer:** {answers[0]}")
            md_lines.append(f"**Context:** {context[:500]}...")
            md_lines.append("")

        save_document("squad-v2-sample.md", "\n".join(md_lines), "https://rajpurkar.github.io/SQuAD-explorer/")
        return True

    except Exception as e:
        print(f"  [FAIL] SQuAD download failed: {e}")
        # Fallback: create a manual sample
        return create_squad_fallback()


def create_squad_fallback():
    """Create a small SQuAD-like sample if download fails."""
    content = """# SQuAD v2.0 — Sample QA Pairs (Fallback)

> Source: https://rajpurkar.github.io/SQuAD-explorer/
> SQuAD (Stanford Question Answering Dataset) is a reading comprehension dataset.

## Overview

SQuAD v2.0 is a collection of question-answer pairs derived from Wikipedia articles.
It includes both answerable and unanswerable questions to test a system's ability
to know when no answer is supported by the passage.

## Sample Passage 1: Quantum Computing

Quantum computing is a type of computation that harnesses the collective properties
of quantum states, such as superposition, interference, and entanglement, to perform
calculations. The devices that perform quantum computations are known as quantum computers.

Q: What properties of quantum states does quantum computing harness?
A: superposition, interference, and entanglement

Q: What are the devices that perform quantum computations called?
A: quantum computers

Q: Who invented quantum computing? (unanswerable from passage)

## Sample Passage 2: Machine Learning

Machine learning (ML) is a field of inquiry devoted to understanding and building
methods that "learn" – that is, methods that leverage data to improve performance
on some set of tasks. It is seen as a part of artificial intelligence.

Q: What is machine learning a part of?
A: artificial intelligence

Q: What do ML methods leverage to improve performance?
A: data

## Sample Passage 3: Geographic Information Systems

A geographic information system (GIS) is a system that creates, manages, analyzes,
and maps all types of data. GIS connects data to a map, integrating location data
with descriptive information.

Q: What does GIS stand for?
A: geographic information system

Q: What does GIS connect data to?
A: a map
"""
    save_document("squad-v2-fallback.md", content, "https://rajpurkar.github.io/SQuAD-explorer/")
    return False


def download_chinese_qa_sample():
    """Download or create Chinese QA samples."""
    print("\n" + "=" * 60)
    print("  2b. Chinese QA Dataset Samples")
    print("=" * 60)

    # Try to get CMRC (Chinese Machine Reading Comprehension)
    try:
        from datasets import load_dataset
        dataset = load_dataset("cmrc2018", split="train", trust_remote_code=True)
        subset = dataset.select(range(min(500, len(dataset))))
        json_path = OUTPUT_DIR / "cmrc2018-train.json"
        subset.to_json(str(json_path))
        print(f"  [OK] cmrc2018-train.json ({json_path.stat().st_size:,} bytes)")
        return True
    except Exception as e:
        print(f"  [WARN] CMRC download failed: {e}")

    # Try WebQA (Baidu Zhidao)
    try:
        from datasets import load_dataset
        dataset = load_dataset("web_qa", split="train", trust_remote_code=True)
        subset = dataset.select(range(min(500, len(dataset))))
        json_path = OUTPUT_DIR / "webqa-train.json"
        subset.to_json(str(json_path))
        print(f"  [OK] webqa-train.json ({json_path.stat().st_size:,} bytes)")
        return True
    except Exception as e:
        print(f"  [WARN] WebQA download failed: {e}")

    # Create fallback Chinese QA
    content = """# 中文问答数据集样本 (Chinese QA Sample)

> 这是一组手工构建的中文问答对，涵盖地理信息、人工智能、量子计算等主题。
> 用于评估RAG系统在中文语境下的检索和问答能力。

## 地理信息系统

### Q1: GIS的全称是什么？
A: Geographic Information System（地理信息系统）

### Q2: GIS由哪几部分组成？
A: GIS通常由硬件、软件、数据、人员和方法五个基本部分组成。

### Q3: 矢量数据和栅格数据有什么区别？
A: 矢量数据用点、线、面表示空间要素，适合表达离散对象（如道路、建筑）；
栅格数据用规则网格单元表示空间，适合表达连续现象（如高程、温度）。

### Q4: 什么是空间分析？
A: 空间分析是对地理空间数据进行操作和分析的技术，包括缓冲区分析、叠加分析、
网络分析、地形分析等。

### Q5: ArcGIS Pro与ArcMap有哪些主要区别？
A: ArcGIS Pro采用64位架构，支持多线程处理，具有现代化的Ribbon界面；
ArcMap是32位程序，界面更传统。ArcGIS Pro支持3D和2D一体化显示，
而ArcMap需要ArcScene进行3D可视化。

### Q6: 什么是地理数据库(Geodatabase)？
A: 地理数据库是ArcGIS的原生数据结构，用于存储和管理空间数据和属性数据。
它支持要素类、要素数据集、拓扑、网络数据集等高级地理数据模型。

## 量子计算

### Q7: 什么是量子比特(Qubit)？
A: 量子比特是量子计算的基本信息单位。与经典比特只能为0或1不同，
量子比特可以同时处于0和1的叠加态。

### Q8: Shor算法解决什么问题？
A: Shor算法可以在多项式时间内进行大整数分解，对RSA加密等基于大数分解
的公钥密码系统构成威胁。

### Q9: 量子纠缠是什么？
A: 量子纠缠是指两个或多个量子粒子之间存在一种特殊关联，无论它们相隔多远，
对其中一个粒子的测量会立即影响另一个粒子的状态。

## 大语言模型与AI

### Q10: RAG（检索增强生成）的核心思想是什么？
A: RAG的核心思想是在大语言模型生成答案之前，先从外部知识库中检索相关信息，
然后将检索到的信息与用户查询一起输入模型，从而增强答案的准确性和时效性。

### Q11: 什么是提示注入攻击？
A: 提示注入攻击是指攻击者通过构造恶意的输入指令，覆盖或修改系统的原始提示，
使模型执行非预期的行为。

### Q12: Agent在AI系统中是什么角色？
A: Agent是能够感知环境、做出决策并采取行动的自主实体。在LLM系统中，
Agent通常利用语言模型进行推理，并可以调用工具（搜索、代码执行等）
来完成复杂任务。
"""
    save_document("chinese-qa-sample.md", content, "manual compilation")
    return False


def download_nq_sample():
    """Download Natural Questions sample."""
    print("\n" + "=" * 60)
    print("  2c. Natural Questions Dataset")
    print("=" * 60)

    try:
        from datasets import load_dataset
        dataset = load_dataset("natural_questions", split="train", trust_remote_code=True)
        # NQ is huge; take a sample
        subset = dataset.select(range(min(500, len(dataset))))
        json_path = OUTPUT_DIR / "natural-questions-sample.json"
        subset.to_json(str(json_path))
        print(f"  [OK] natural-questions-sample.json ({json_path.stat().st_size:,} bytes)")
        return True
    except Exception as e:
        print(f"  [WARN] Natural Questions download failed: {e}")

    # Fallback
    content = """# Natural Questions Sample (Fallback)

Natural Questions (NQ) is a dataset by Google for open-domain question answering.
It contains real anonymized Google queries and Wikipedia pages.

## Sample QA Pairs

Q: what is the definition of a geographic information system
A: A geographic information system (GIS) is a conceptualized framework that
provides the ability to capture and analyze spatial and geographic data.

Q: when did post quantum cryptography become a nist standard
A: NIST released its first post-quantum cryptography standards in August 2024,
including FIPS 203 (ML-KEM), FIPS 204 (ML-DSA), and FIPS 205 (SLH-DSA).

Q: how does retrieval augmented generation work
A: Retrieval-Augmented Generation (RAG) works by first retrieving relevant
documents from a knowledge base in response to a query, then providing those
documents as context to a language model to generate a more accurate answer.

Q: what is arcgis pro used for
A: ArcGIS Pro is a desktop GIS application used for mapping, spatial analysis,
data management, and visualization. It supports 2D and 3D mapping, geoprocessing
tools, and integrates with ArcGIS Online and ArcGIS Enterprise.
"""
    save_document("natural-questions-fallback.md", content, "https://ai.google.com/research/NaturalQuestions")
    return False


# ══════════════════════════════════════════════════════════════════════
# 3. NIST Publications & Technical Documents
# ══════════════════════════════════════════════════════════════════════

NIST_URLS = {
    # PQC Standards
    "nist-fips203-ml-kem": "https://csrc.nist.gov/pubs/fips/203/final",
    "nist-fips204-ml-dsa": "https://csrc.nist.gov/pubs/fips/204/final",
    "nist-fips205-slh-dsa": "https://csrc.nist.gov/pubs/fips/205/final",
    "nist-pqc-overview": "https://csrc.nist.gov/projects/post-quantum-cryptography",
    "nist-pqc-selected-algorithms": "https://csrc.nist.gov/projects/post-quantum-cryptography/selected-algorithms-2022",

    # AI Standards
    "nist-ai-rmf": "https://www.nist.gov/itl/ai-risk-management-framework",
    "nist-ai-100-1": "https://csrc.nist.gov/pubs/ai/100/1/e2023/final",

    # Cybersecurity
    "nist-csf": "https://www.nist.gov/cyberframework",
    "niso-sp800-53": "https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final",
}


def download_nist_docs():
    """Download NIST documentation."""
    print("\n" + "=" * 60)
    print("  3a. Downloading NIST Publications")
    print("=" * 60)

    success = 0
    for slug, url in NIST_URLS.items():
        print(f"\n  [{slug}]")
        html = fetch_url(url)
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else slug

        text = html_to_markdown_text(html, url)
        if not text or len(text) < 200:
            print(f"    [WARN] Too little content ({len(text)} chars), skipping")
            continue

        full_content = f"# {title}\n\n> Source: {url}\n\n{text}"
        filename = f"nist--{slug}.md"
        save_document(filename, full_content, url)
        success += 1
        time.sleep(DELAY_BETWEEN_REQUESTS)

    print(f"\n  [OK] Downloaded {success}/{len(NIST_URLS)} NIST pages")
    return success


# ══════════════════════════════════════════════════════════════════════
# 4. Wikipedia Articles
# ══════════════════════════════════════════════════════════════════════

WIKI_TOPICS = {
    "geographic-information-system": "https://en.wikipedia.org/wiki/Geographic_information_system",
    "spatial-analysis": "https://en.wikipedia.org/wiki/Spatial_analysis",
    "remote-sensing": "https://en.wikipedia.org/wiki/Remote_sensing",
    "cartography": "https://en.wikipedia.org/wiki/Cartography",
    "geodesy": "https://en.wikipedia.org/wiki/Geodesy",
    "post-quantum-cryptography": "https://en.wikipedia.org/wiki/Post-quantum_cryptography",
    "quantum-cryptography": "https://en.wikipedia.org/wiki/Quantum_cryptography",
    "shor-algorithm": "https://en.wikipedia.org/wiki/Shor%27s_algorithm",
    "lattice-based-cryptography": "https://en.wikipedia.org/wiki/Lattice-based_cryptography",
    "retrieval-augmented-generation": "https://en.wikipedia.org/wiki/Retrieval-augmented_generation",
    "large-language-model": "https://en.wikipedia.org/wiki/Large_language_model",
    "machine-learning": "https://en.wikipedia.org/wiki/Machine_learning",
    "deep-learning": "https://en.wikipedia.org/wiki/Deep_learning",
    "artificial-intelligence-ethics": "https://en.wikipedia.org/wiki/Ethics_of_artificial_intelligence",
    "regulation-of-ai": "https://en.wikipedia.org/wiki/Regulation_of_artificial_intelligence",
    "eu-ai-act": "https://en.wikipedia.org/wiki/Artificial_Intelligence_Act",
    "prompt-engineering": "https://en.wikipedia.org/wiki/Prompt_engineering",
    "multi-agent-system": "https://en.wikipedia.org/wiki/Multi-agent_system",
    "arcgis": "https://en.wikipedia.org/wiki/ArcGIS",
    "esri": "https://en.wikipedia.org/wiki/Esri",
    "web-mapping": "https://en.wikipedia.org/wiki/Web_mapping",
    "geospatial-analysis": "https://en.wikipedia.org/wiki/Geospatial_analysis",
    "digital-elevation-model": "https://en.wikipedia.org/wiki/Digital_elevation_model",
    "coordinate-reference-system": "https://en.wikipedia.org/wiki/Spatial_reference_system",
    "geocoding": "https://en.wikipedia.org/wiki/Geocoding",
}


def download_wikipedia():
    """Download Wikipedia articles."""
    print("\n" + "=" * 60)
    print("  3b. Downloading Wikipedia Articles")
    print("=" * 60)

    success = 0
    for slug, url in WIKI_TOPICS.items():
        print(f"\n  [{slug}]")
        html = fetch_url(url)
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.find("title")
        # Clean up " - Wikipedia" suffix
        title = title_tag.get_text(strip=True).replace(" - Wikipedia", "") if title_tag else slug

        # Extract main content — pass full HTML; function will find the right div
        text = html_to_markdown_text(html, url)
        if not text or len(text) < 500:
            print(f"    [WARN] Too little content ({len(text)} chars)")
            continue

        full_content = (
            f"# {title}\n\n"
            f"> Source: {url}\n"
            f"> License: CC BY-SA 4.0 (Wikipedia)\n\n"
            f"{text}"
        )
        filename = f"wiki--{slug}.md"
        save_document(filename, full_content, url)
        success += 1
        time.sleep(DELAY_BETWEEN_REQUESTS)

    print(f"\n  [OK] Downloaded {success}/{len(WIKI_TOPICS)} Wikipedia articles")
    return success


# ══════════════════════════════════════════════════════════════════════
# 5. Additional Technical Documentation
# ══════════════════════════════════════════════════════════════════════

def create_synthetic_docs():
    """Create synthetic technical documents for RAG evaluation diversity."""
    print("\n" + "=" * 60)
    print("  4. Creating Synthetic Technical Documents")
    print("=" * 60)

    docs = {
        "gis-fundamentals.md": """# GIS Fundamentals — A Technical Primer

> Source: Synthetic document for RAG evaluation
> Topics: GIS concepts, data models, spatial analysis

## Introduction to GIS

A Geographic Information System (GIS) is a framework for gathering, managing,
and analyzing data. Rooted in the science of geography, GIS integrates many
types of data. It analyzes spatial location and organizes layers of information
into visualizations using maps and 3D scenes.

## Data Models

### Vector Data Model

Vector data represents geographic features as discrete objects: points, lines,
and polygons. Each feature has attributes stored in a table.

- **Points**: Represent discrete locations (e.g., cities, wells, sensors)
- **Lines**: Represent linear features (e.g., roads, rivers, pipelines)
- **Polygons**: Represent area features (e.g., lakes, parcels, countries)

### Raster Data Model

Raster data represents the world as a grid of cells (pixels). Each cell stores
a single value representing information such as elevation, temperature, or land
cover classification.

Key characteristics:
- Cell size (spatial resolution)
- Number of rows and columns
- Single or multiple bands
- Continuous vs. discrete values

### TIN (Triangulated Irregular Network)

A TIN is a vector-based representation of a continuous surface, constructed
from a set of irregularly spaced points. TINs are commonly used for high-precision
terrain modeling.

## Coordinate Systems

### Geographic Coordinate Systems (GCS)

Uses a three-dimensional spherical surface to define locations on the Earth.
Locations are measured in angular units (degrees) of latitude and longitude.

Common GCS: WGS 84, NAD83, CGCS2000

### Projected Coordinate Systems (PCS)

A PCS projects the Earth's curved surface onto a flat, two-dimensional plane.
Locations are measured in linear units (meters, feet).

Common projections:
- **Mercator**: Preserves angles, distorts area
- **UTM (Universal Transverse Mercator)**: Divides Earth into 60 zones
- **Albers Equal Area**: Preserves area, good for regional mapping
- **Lambert Conformal Conic**: Preserves shape for mid-latitude regions

## Spatial Analysis Methods

### Buffer Analysis

Creates zones of a specified distance around features.

### Overlay Analysis

Combines multiple layers to identify relationships:
- **Intersect**: Areas common to all inputs
- **Union**: All areas from all inputs combined
- **Erase**: Removes areas of one input from another

### Network Analysis

Analyzes transportation networks:
- Shortest path
- Service area
- Location-allocation
- OD cost matrix

### Surface Analysis

Analyzes continuous surfaces (e.g., elevation):
- Slope, aspect, hillshade
- Viewshed analysis
- Contour generation
- Cut/fill calculations

### Statistical Analysis

- **Hot Spot Analysis (Getis-Ord Gi*)**: Identifies statistically significant
  clusters of high and low values
- **Spatial Autocorrelation (Moran's I)**: Measures how clustered or dispersed
  features are
- **Kriging**: Advanced geostatistical interpolation method

## Geodatabase Concepts

The geodatabase is the native data structure for ArcGIS and is the primary data
format used for editing and data management. It supports:

- **Feature classes**: Collections of geographic features with the same geometry type
- **Feature datasets**: Collections of feature classes that share a coordinate system
- **Topology**: Rules defining how features share geometry
- **Relationship classes**: Associations between feature classes or tables
- **Network datasets**: Connectivity models for transportation networks
- **Mosaic datasets**: Manage and serve large collections of raster data
""",

        "multi-agent-architectures.md": """# Multi-Agent System Architectures for Research

> Source: Synthetic document for RAG evaluation
> Topics: AI agents, orchestration, LangGraph, AutoGen

## Overview

Multi-agent systems (MAS) consist of multiple interacting intelligent agents.
In the context of large language models (LLMs), each agent typically has access
to a language model plus a set of tools (search, code execution, APIs).

## Common Patterns

### Fan-out / Fan-in

A coordinator dispatches a query to multiple specialist agents in parallel
(fan-out), collects their responses, and merges the results (fan-in).

**Advantages:**
- Parallel execution reduces latency
- Isolated contexts prevent cross-contamination
- Specialist agents can use different tools/instructions

**Disadvantages:**
- Higher token cost (multiple agents)
- Requires robust result merging

### Sequential Pipeline

Agents execute in sequence: the output of Agent A becomes the input of Agent B.

**Use cases:**
- Retrieve → Verify → Generate
- Research → Draft → Review → Publish

### Debate / Arbitration

Multiple agents independently answer the same question, then compare results.
Disagreements can trigger additional research or human review.

### Hierarchical

A supervisor agent delegates sub-tasks to worker agents and assembles the final
output. Common in frameworks like AutoGen and LangGraph's Supervisor pattern.

## Key Design Decisions

### State Management

How does the system persist and share state between agents?

- **Centralized state** (LangGraph StateGraph): Single source of truth
- **Message passing** (AutoGen): Agents communicate via messages
- **Blackboard**: Shared workspace all agents can read/write

### Tool Access

Which agents get which tools?

- **Equal access**: All agents have the same toolbox
- **Role-based**: Each agent gets tools matching its specialty
- **On-demand**: Tools are dynamically provisioned

### Source Status Protocol

When agents retrieve from different sources (RAG, Web, Model knowledge), each
source result should carry:
- `status`: success | failed | fallback
- `latency_ms`: response time
- `error`: explanation if failed/fallback

Failed sources are excluded from evidence graphs and consensus voting.

## Evaluation Considerations

### Retrieval Quality

- **Recall@k**: Proportion of relevant documents in top-k results
- **Precision@k**: Proportion of top-k results that are relevant
- **MRR (Mean Reciprocal Rank)**: Average of reciprocal ranks of the first relevant result

### Report Quality

- **Factual accuracy**: Claims supported by sources
- **Source coverage**: All expected sources consulted
- **Conflict resolution**: Disagreements properly handled
- **Uncertainty communication**: Limitations stated clearly

### Robustness

- **Failed source handling**: Graceful degradation when a source is unavailable
- **Prompt injection resistance**: Retrieved text treated as data, not instruction
- **Hallucination detection**: Claims traceable to sources
""",

        "rag-technical-deep-dive.md": """# Retrieval-Augmented Generation: A Technical Deep Dive

> Source: Synthetic document for RAG evaluation
> Topics: RAG architecture, chunking, retrieval, fusion

## What is RAG?

Retrieval-Augmented Generation (RAG) is a technique that enhances LLM outputs
by retrieving relevant information from an external knowledge base before
generating a response. First introduced by Lewis et al. (2020), RAG addresses
key LLM limitations: knowledge cutoff, hallucination, and lack of source
attribution.

## Architecture

### 1. Document Ingestion

Raw documents go through a preprocessing pipeline:
1. **Parsing**: Extract text from PDF, HTML, Markdown, etc.
2. **Chunking**: Split into manageable segments
3. **Embedding**: Convert chunks to dense vectors
4. **Indexing**: Store vectors in a vector database

### 2. Retrieval

When a query arrives:
1. **Query embedding**: Convert the query to a vector
2. **Similarity search**: Find nearest chunks in vector space
3. **Reranking** (optional): Reorder results with a cross-encoder

### 3. Generation

The retrieved chunks are inserted into the prompt as context:
```
Answer the question based on the following context:

[Context from retrieved chunks]

Question: {user query}
Answer:
```

## Chunking Strategies

### Fixed-Size Chunking

Split text into fixed-size segments with optional overlap.

**Pros:** Simple, predictable
**Cons:** May split in the middle of sentences or semantic units

### Semantic Chunking

Split at natural boundaries (paragraphs, sections).

**Pros:** Maintains semantic coherence
**Cons:** Inconsistent chunk sizes

### Parent-Child Chunking (Conflux Approach)

Two-level hierarchy:
- **L1 Parent (1024 chars)**: Larger chunks for context
- **L2 Child (256 chars)**: Smaller chunks for precise retrieval

During retrieval, child chunks are matched, then their parent context is
included for richer generation.

### Sentence Window

Retrieve a sentence, expand to include surrounding sentences.

## Retrieval Methods

### Dense Retrieval (Vector Similarity)

Uses embedding models (e.g., text-embedding-3-small) to encode both documents
and queries into the same vector space. Retrieval is by cosine similarity or
Euclidean distance.

**Strengths:** Captures semantic meaning, handles paraphrasing
**Weaknesses:** May miss exact keyword matches, embedding model quality matters

### Sparse Retrieval (BM25)

Statistical method based on term frequency and inverse document frequency.
No embeddings required.

**Strengths:** Good for exact keyword matching, interpretable
**Weaknesses:** Misses semantic equivalences (synonyms)

### Hybrid Retrieval

Combines dense and sparse scores, typically with Reciprocal Rank Fusion (RRF):

```
RRF_score(d) = Σ (1 / (k + rank_i(d)))
```

Where k is a constant (typically 60) and rank_i is the document's rank in
retrieval method i.

Conflux uses a weighted variant:
```
score = dense_weight × dense_score + bm25_weight × bm25_score
```

## Evaluation Metrics

| Metric | Description |
|--------|------------|
| Recall@k | Fraction of relevant docs in top-k results |
| Hit Rate | Fraction of queries with ≥1 relevant result in top-k |
| MRR | Mean reciprocal rank of the first relevant result |
| NDCG@k | Normalized discounted cumulative gain |

## Common Challenges

1. **Irrelevant retrieval**: Retrieved chunks don't answer the question
2. **Context overflow**: Too many/large chunks exceed model context window
3. **Stale index**: Knowledge base not updated with new information
4. **Low-quality chunking**: Chunks break semantic units
5. **Embedding mismatch**: Query and document embeddings not well aligned
""",

        "ai-governance-comparison.md": """# AI Governance: A Global Comparative Overview

> Source: Synthetic document for RAG evaluation
> Topics: AI regulation, EU AI Act, China AI law, US AI policy

## European Union: The AI Act

The EU AI Act (Regulation 2024/1689) is the world's first comprehensive AI law.
It entered into force on August 1, 2024, with phased implementation through 2027.

### Risk-Based Approach

| Risk Level | Examples | Regulatory Burden |
|-----------|----------|-------------------|
| Unacceptable | Social scoring, real-time biometric surveillance in public | Prohibited |
| High | Employment, education, law enforcement, critical infrastructure | Conformity assessment, risk management, human oversight |
| Limited | Chatbots, emotion recognition | Transparency obligations |
| Minimal | Spam filters, AI-enabled video games | Voluntary codes of conduct |

### Key Requirements for High-Risk AI

- Risk management system throughout the AI lifecycle
- Data governance and data quality management
- Technical documentation and record-keeping
- Transparency and provision of information to users
- Human oversight measures
- Accuracy, robustness, and cybersecurity

### General-Purpose AI (GPAI) Provisions

- All GPAI models: technical documentation, copyright policy, training data summary
- GPAI with systemic risk: model evaluation, adversarial testing, incident reporting
- Codes of practice developed by the AI Office

### Penalties

- Up to €35 million or 7% of global annual turnover for prohibited practices
- Up to €15 million or 3% for most other violations
- Up to €7.5 million or 1.5% for supplying incorrect information

## China: Sectoral and Phased Approach

China has adopted a more sectoral approach, regulating AI through a patchwork
of laws, regulations, and technical standards.

### Key Regulations

- **Interim Measures for the Management of Generative AI Services** (2024):
  - Applied to text, image, audio, video, and other content generation
  - Requires respect for intellectual property rights
  - Prohibits discrimination based on ethnicity, race, gender, etc.
  - Content must be truthful and accurate

- **Provisions on the Administration of Algorithmic Recommendations** (2022):
  - Regulates recommendation algorithms
  - Requires transparency about algorithm operations
  - Users must be able to opt out of personalized recommendations

- **Personal Information Protection Law (PIPL)** (2021):
  - Comprehensive data protection law
  - Applies to automated decision-making, including AI

### Key Principles

- Socialist core values must be upheld
- Content security and censorship
- Protection of national security and social stability
- Protection of citizens' legitimate rights

## United States: Executive and Agency-Led Approach

The US has not passed a comprehensive federal AI law. Instead, regulation
proceeds through executive orders and agency actions.

### Executive Order 14110 (2023)

- Safe, Secure, and Trustworthy Development and Use of AI
- Requires developers of powerful AI systems to share safety test results
- NIST to develop standards for red-teaming
- Commerce Department to develop guidance for content authentication

### State-Level Regulation

- Colorado AI Act (2024): First comprehensive state AI law in the US
- California: Multiple proposed AI bills, including safety and transparency
- New York: Local Law 144 on automated employment decision tools

### Agency Actions

- FTC: Enforcement actions against deceptive AI claims
- FDA: AI/ML in medical devices regulatory framework
- SEC: Proposed rules on AI use by financial firms

## Comparison Summary

| Dimension | EU | China | US |
|-----------|-----|-------|-----|
| Approach | Comprehensive legislation | Sectoral regulations | Executive orders + state laws |
| Risk framework | 4-tier | Content-based | Emerging |
| Enforcement | GDPR-style fines | Government oversight | Agency-led |
| Innovation emphasis | Trustworthy AI | Strategic autonomy | Maintaining leadership |
| Transparency | Required across levels | Required for recommendation algorithms | Developing |
""",

        "spatial-data-science.md": """# Spatial Data Science: Methods and Applications

> Source: Synthetic document for RAG evaluation
> Topics: Spatial statistics, machine learning for GIS, GeoAI

## Introduction

Spatial Data Science combines geographic information systems (GIS) with data
science methods to analyze location-based data. It extends traditional data
science by accounting for the special properties of spatial data: spatial
autocorrelation, spatial heterogeneity, and the modifiable areal unit problem
(MAUP).

## Key Concepts

### Spatial Autocorrelation

Tobler's First Law of Geography: "Everything is related to everything else,
but near things are more related than distant things."

Measures:
- **Moran's I**: Global measure of spatial autocorrelation (-1 to +1)
- **Getis-Ord Gi***: Local indicator of spatial association (hot/cold spots)
- **LISA (Local Indicators of Spatial Association)**: Identifies clusters and outliers

### Spatial Heterogeneity

The uneven distribution of phenomena across space. Models must account for
varying relationships in different geographic areas.

Techniques:
- Geographically Weighted Regression (GWR)
- Multiscale GWR (MGWR)
- Spatial regime models

### Modifiable Areal Unit Problem (MAUP)

Statistical results can change depending on the spatial units used for analysis.
Two aspects:
- **Scale effect**: Different results at different aggregation levels
- **Zoning effect**: Different results with different boundary configurations

## Machine Learning for Spatial Data

### Traditional ML with Spatial Features

- Feature engineering: distance to amenities, spatial lag variables, density measures
- Models: Random Forest, XGBoost, GBM with spatial cross-validation
- Spatial cross-validation: Block CV, spatial buffered CV

### Deep Learning for Spatial Data

- **CNNs for satellite imagery**: Land cover classification, object detection
- **Graph Neural Networks**: Spatial networks, traffic prediction
- **Point cloud processing**: LiDAR classification, 3D building extraction

### GeoAI

The intersection of GIS and artificial intelligence:
- Automated feature extraction from imagery
- Predictive modeling with spatial constraints
- Natural language processing for geospatial text
- Spatial reasoning in LLMs

## Common Analyses

### Site Selection / Suitability Analysis

Multi-criteria evaluation combining weighted layers:
```
Suitability = Σ (w_i × criterion_i)
```

### Spatial Interpolation

Estimating values at unsampled locations:
- **Deterministic**: IDW, Natural Neighbor, Spline
- **Geostatistical**: Kriging (Ordinary, Universal, Co-Kriging)

### Cluster Analysis

- **DBSCAN**: Density-based spatial clustering
- **HDBSCAN**: Hierarchical density-based clustering
- **Spatial scan statistics (Kulldorff's scan)**: Detecting clusters in space and time

### Space-Time Analysis

- Space-time cubes for emerging hot spot analysis
- Space-time kernel density estimation
- Trajectory analysis for movement data

## Tools and Platforms

| Tool | Type | Key Strengths |
|------|------|---------------|
| ArcGIS Pro | Desktop | Comprehensive geoprocessing, spatial statistics |
| QGIS | Desktop (FOSS) | Extensive plugin ecosystem, Python scripting |
| GeoPandas | Python library | Vector data processing with Pandas-like API |
| Rasterio/Xarray | Python library | Raster data processing |
| PySAL | Python library | Spatial econometrics, spatial statistics |
| Google Earth Engine | Cloud platform | Petabyte-scale satellite imagery analysis |
| PostGIS | Database | Spatial extension for PostgreSQL |
""",
    }

    for filename, content in docs.items():
        save_document(filename, content, "synthetic")

    return len(docs)


# ══════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════

def main():
    global OUTPUT_DIR

    parser = argparse.ArgumentParser(description="Download RAG corpus documents")
    parser.add_argument(
        "--targets",
        default="all",
        help="Comma-separated: esri,qa,nist,wiki,synthetic,all"
    )
    parser.add_argument(
        "--output-dir",
        default=str(OUTPUT_DIR),
        help=f"Output directory (default: {OUTPUT_DIR})"
    )
    args = parser.parse_args()

    OUTPUT_DIR = Path(args.output_dir)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    targets = set(t.strip() for t in args.targets.split(","))
    if "all" in targets:
        targets = {"esri", "qa", "nist", "wiki", "synthetic"}

    print("=" * 60)
    print("  Conflux RAG Corpus Downloader")
    print(f"  Output: {OUTPUT_DIR}")
    print(f"  Targets: {', '.join(sorted(targets))}")
    print("=" * 60)

    total = 0

    if "esri" in targets:
        total += download_esri_docs()

    if "qa" in targets:
        download_squad_v2()
        download_chinese_qa_sample()
        download_nq_sample()

    if "nist" in targets:
        total += download_nist_docs()

    if "wiki" in targets:
        total += download_wikipedia()

    if "synthetic" in targets:
        total += create_synthetic_docs()

    # ── Summary ──
    print("\n" + "=" * 60)
    print("  Download Summary")
    print("=" * 60)
    files = sorted(OUTPUT_DIR.glob("*"))
    for f in files:
        size_kb = f.stat().st_size / 1024
        print(f"  {f.name}  ({size_kb:.1f} KB)")
    print(f"\n  Total files: {len(files)}")
    total_size = sum(f.stat().st_size for f in files) / 1024
    print(f"  Total size: {total_size:.1f} KB")


if __name__ == "__main__":
    main()
