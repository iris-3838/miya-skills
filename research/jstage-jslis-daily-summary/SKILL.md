---
name: jstage-jslis-daily-summary
description: "J-STAGE + CiNii daily paper summaries in Japanese for LIS research."
version: 1.1
author: Hermes Agent
license: MIT
---

# J-STAGE JSLIS Daily Summary

Daily summary of new papers from J-STAGE and CiNii covering Library and Information Science, philosophy of information, and related fields.

## Triggers
- Cron job: daily morning summary
- On-demand: `@agent publish summary` or `@agent 今日の論文`

## Workflow
1. Scrape J-STAGE and CiNii for papers matching LIS keywords
2. Generate Japanese-language summaries
3. Post to designated channel (Discord)

## Keywords
- 図書館情報学 (Library and Information Science)
- 情報哲学 (Philosophy of Information)
- 情報基礎論 (Foundations of Information)
- ルチアーノ・フロリディ (Luciano Floridi)
- IEKO/ISKO related content

## Aliases
- `jstage-daily`
- `J-STAGE daily`
- `今日の論文`

## Complementary Coverage
This skill covers **Japanese-language LIS literature** (J-STAGE, CiNii).
For **English/international LIS literature**, use `openalex-literature-survey` skill, which surveys JDoc, JASIST, KO, Library Trends, ASIS&T Proceedings, and other international venues via the OpenAlex API.
