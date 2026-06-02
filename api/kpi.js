// api/kpi.js — LOOK UP Light KPI集計API
// Notion クライアントマスタから「紹介元 = freee税理士紹介」のリードを取得し、
// 確定したKPI定義どおりに集計してJSONで返す。
//
// 必要な環境変数:
//   NOTION_TOKEN         … Notion Integration Token (ntn_...)
//   NOTION_DATABASE_ID   … クライアントマスタDBのID
//   MONTHLY_GOAL         … (任意) 今月の契約目標。未設定なら 10

const NOTION_TOKEN = process.env.NOTION_TOKEN;
const DB = process.env.NOTION_DATABASE_ID;
const GOAL = Number(process.env.MONTHLY_GOAL || 10);

// ---- プロパティ名（Notion DBの実際の列名と一致させること）----
const P = {
  id: "管理ID",
  name: "顧問先ページ",
  toiawase: "問い合わせ日",
  yotei: "面談予定日",
  jisshi: "面談実施日",
  gijiroku: "議事録・見積送付日",
  teiketsu: "契約締結予定日",
  kaishi: "契約開始日",
  lifecycle: "ライフサイクルステータス",
  source: "紹介元",
  jisshisha: "面談実施者",
};
const SOURCE_VALUE = "freee税理士紹介";

// ---- Notionからフィルタ付きで全件取得（ページング）----
async function queryAll() {
  let results = [], cursor, more = true, guard = 0;
  while (more && guard++ < 20) {
    const res = await fetch(`https://api.notion.com/v1/databases/${DB}/query`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${NOTION_TOKEN}`,
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        filter: { property: P.source, select: { equals: SOURCE_VALUE } },
        page_size: 100,
        ...(cursor ? { start_cursor: cursor } : {}),
      }),
    });
    const j = await res.json();
    if (j.object === "error") throw new Error(j.message || "Notion API error");
    results = results.concat(j.results || []);
    more = j.has_more;
    cursor = j.next_cursor;
  }
  return results;
}

// ---- プロパティ抽出ヘルパー ----
const getDate = (p, k) => p[k]?.date?.start || null;        // "YYYY-MM-DD" or ISO datetime
const getSel = (p, k) => p[k]?.select?.name || null;
const getTitle = (p, k) => p[k]?.title?.[0]?.plain_text || "";
const getNum = (p, k) => (p[k]?.number ?? null);
const getMulti = (p, k) => (p[k]?.multi_select || []).map((o) => o.name);
const getText = (p, k) => {
  const v = p[k];
  if (!v) return "";
  if (v.rich_text) return v.rich_text.map((t) => t.plain_text).join("");
  if (v.title) return v.title.map((t) => t.plain_text).join("");
  if (v.select) return v.select.name || "";
  return "";
};

const ymOf = (d) => (d ? d.slice(0, 7) : null);   // "2026-06"
const dayOf = (d) => (d ? d.slice(0, 10) : null);  // "2026-06-01"

export default async function handler(req, res) {
  try {
    if (!NOTION_TOKEN || !DB) {
      return res.status(500).json({ error: "NOTION_TOKEN / NOTION_DATABASE_ID が未設定です" });
    }

    const raw = await queryAll();
    const rows = raw.map((r) => {
      const p = r.properties;
      return {
        id: getNum(p, P.id),
        name: getTitle(p, P.name),
        toiawase: getDate(p, P.toiawase),
        yotei: getDate(p, P.yotei),
        jisshi: getDate(p, P.jisshi),
        gijiroku: getDate(p, P.gijiroku),
        teiketsu: getDate(p, P.teiketsu),
        kaishi: getDate(p, P.kaishi),
        lifecycle: getSel(p, P.lifecycle),
        jisshisha: getMulti(p, P.jisshisha),
        gyo: getText(p, "業種"),
      };
    });

    // ---- 今月 / 先月（JST基準）----
    const nowJst = new Date(Date.now() + 9 * 3600e3);
    const ym = nowJst.toISOString().slice(0, 7);
    const lastJst = new Date(Date.UTC(nowJst.getUTCFullYear(), nowJst.getUTCMonth() - 1, 1));
    const lastYm = lastJst.toISOString().slice(0, 7);
    const todayStr = nowJst.toISOString().slice(0, 10);
    const hhmm = nowJst.toISOString().slice(11, 16);
    const updatedAt = `${ym.replace("-", "/")}/${todayStr.slice(8)} ${hhmm}`;

    const inMonth = (d, m) => d && ymOf(d) === m;
    const cntM = (key, m) => rows.filter((r) => inMonth(r[key], m)).length;

    // ---- 今月のファネル & KPI ----
    const leads = cntM("toiawase", ym);
    const scheduled = cntM("yotei", ym);
    const met = cntM("jisshi", ym);
    const won = cntM("kaishi", ym);
    // 成約率：直近2か月（今月＋先月）に面談実施したリードのうち、契約に至った割合（コホート）
    const cohortMonths = [ym, lastYm];
    const cohort = rows.filter((r) => r.jisshi && cohortMonths.includes(ymOf(r.jisshi)));
    const cohortWon = cohort.filter((r) => r.kaishi).length;
    const closeRate = cohort.length ? Math.round((cohortWon / cohort.length) * 100) : 0;

    const leadsL = cntM("toiawase", lastYm);
    const metL = cntM("jisshi", lastYm);
    const wonL = cntM("kaishi", lastYm);

    const pct = (a, b) => (b ? Math.round((a / b) * 100) : 0);

    // ---- 日次推移（直近30日・全期間累計：バックフィル）----
    const labels = [], sLeads = [], sSched = [], sMet = [], sWon = [];
    for (let i = 29; i >= 0; i--) {
      const d = new Date(Date.now() + 9 * 3600e3 - i * 86400e3).toISOString().slice(0, 10);
      labels.push(d.slice(5));
      const upto = (key) => rows.filter((r) => r[key] && dayOf(r[key]) <= d).length;
      sLeads.push(upto("toiawase"));
      sSched.push(upto("yotei"));
      sMet.push(upto("jisshi"));
      sWon.push(upto("kaishi"));
    }

    // ---- 入力率（母集団全体）----
    const total = rows.length || 1;
    const fr = (key) => Math.round((rows.filter((r) => r[key]).length / total) * 100);
    const fillRate = [
      { name: "問い合わせ日", v: fr("toiawase") },
      { name: "面談予定日", v: fr("yotei") },
      { name: "面談実施日", v: fr("jisshi") },
      { name: "議事録・見積送付日", v: fr("gijiroku") },
      { name: "契約締結予定日", v: fr("teiketsu") },
      { name: "契約開始日", v: fr("kaishi") },
    ];

    // ---- ライフサイクル分布 ----
    const order = ["面談前", "面談後", "契約締結手続中", "オンボーディング", "契約中", "失注", "連絡途絶"];
    const lcMap = {};
    rows.forEach((r) => { if (r.lifecycle) lcMap[r.lifecycle] = (lcMap[r.lifecycle] || 0) + 1; });
    const lifecycle = order.map((n) => ({ name: n, n: lcMap[n] || 0 }));

    // ---- 要確認：契約中/オンボーディングなのに契約開始日が空 ----
    const attention = rows
      .filter((r) => ["オンボーディング", "契約中"].includes(r.lifecycle) && !r.kaishi)
      .map((r) => ({
        id: r.id != null ? `#${r.id}` : "—",
        name: r.name || "（無題）",
        stage: r.lifecycle,
        who: r.jisshisha[0] || "—",
      }));

    // ---- 内訳リスト（カードをタップしたとき用）----
    const detail = (key, m) =>
      rows
        .filter((r) => inMonth(r[key], m))
        .sort((a, b) => (b[key] || "").localeCompare(a[key] || ""))
        .map((r) => ({
          name: r.name || "（無題）",
          date: dayOf(r[key]),
          stage: r.lifecycle || "—",
          who: r.jisshisha[0] || "—",
          gyo: (r.gyo || "").slice(0, 60) || "—",
        }));

    res.setHeader("Cache-Control", "s-maxage=300, stale-while-revalidate=600");
    return res.status(200).json({
      updatedAt,
      universe: rows.length,
      goal: { target: GOAL, now: won, pct: pct(won, GOAL) },
      month: {
        leads, meetings: met, won, closeRate,
        leadsDelta: leads - leadsL,
        meetingsDelta: met - metL,
        wonDelta: won - wonL,
        cohortSize: cohort.length,
      },
      funnel: { leads, scheduled, met, won, c1: pct(scheduled, leads), c2: pct(met, scheduled), c3: pct(won, met) },
      trend: { labels, leads: sLeads, scheduled: sSched, met: sMet, won: sWon },
      fillRate,
      lifecycle,
      attention,
      details: { leads: detail("toiawase", ym), met: detail("jisshi", ym), won: detail("kaishi", ym) },
    });
  } catch (e) {
    return res.status(500).json({ error: String(e.message || e) });
  }
}
