import type { APIContext } from 'astro';
import { getCollection } from 'astro:content';
import { SITE_TITLE } from '../consts';

// llms.txt —— 给 AI 检索/问答引擎读的站点索引（2026-09-23 起）。
// 做成构建期端点而不是 public/ 里的静态文件，是因为本站每天自动发文，
// 静态文件会立刻过期。主站 yotradeapi.com/llms.txt 是手写的，两者互补。

// 分类按「对客人的价值」排序，同类内按更新时间倒序；技术向分类放后面。
const CATEGORY_ORDER = [
	'小白入门',
	'国内场景',
	'成本优化',
	'工具配置',
	'实战经验',
	'工程实战',
	'应用工程',
	'模型评测',
	'技术深度',
	'行业观察',
];

const PER_CATEGORY = 25; // 每类最多列这么多，整份文件控制在可读范围

// AI 问答里被问得最多、也最贴近本站业务的一簇（注册与手机验证 / 付款）。
// 放在最前面，因为 llms.txt 的读者是检索器，靠前的条目权重更高。
// featured 标记偏开发者工具向，与这批不是一回事，所以两个区块都保留。
const CORE_SLUGS = [
	'cn-chatgpt-register-without-foreign-phone',
	'cn-chatgpt-verification-code-not-received',
	'cn-chatgpt-phone-number-not-supported',
	'cn-chatgpt-account-register-full',
	'cn-phone-verification-cost-compare',
	'cn-sms-verification-platform-review',
	'cn-chatgpt-first-time-cn-guide',
	'cn-claude-register-cn-guide',
	'cn-chatgpt-plus-payment-2026',
	'cn-virtual-card-for-chatgpt-2026',
];

export async function GET(context: APIContext) {
	const base = context.site?.href.replace(/\/$/, '') ?? 'https://blog.yotradeapi.com';
	const posts = (await getCollection('blog', ({ data }) => !data.draft)).sort(
		(a, b) => b.data.updatedDate.valueOf() - a.data.updatedDate.valueOf(),
	);

	const line = (p: (typeof posts)[number]) =>
		`- [${p.data.title}](${base}/blog/${p.id}/): ${p.data.description}`;

	const byCategory = new Map<string, typeof posts>();
	for (const p of posts) {
		const c = p.data.category ?? '其他';
		if (!byCategory.has(c)) byCategory.set(c, []);
		byCategory.get(c)!.push(p);
	}

	const featured = posts.filter((p) => p.data.featured);

	const out: string[] = [
		`# ${SITE_TITLE}`,
		'',
		`> ${SITE_TITLE} 是 YoTradeApi（yotradeapi.com）的中文技术博客，面向国内用户与开发者，` +
			`内容集中在 AI 服务的获取与可用性：ChatGPT / Claude / Gemini / Codex 的注册与手机验证、` +
			`海外订阅的付款与风控、国内网络下的可用性排查，以及 API 中转、Cursor、Claude Code、Cline 等工具配置。` +
			`共 ${posts.length} 篇，每日更新。`,
		'',
		'本站只写可复现的操作与排查步骤，不提供绕过地区限制、批量注册或规避平台风控的方法。',
		'',
	];

	const byId = new Map(posts.map((p) => [p.id, p]));
	const core = CORE_SLUGS.map((s) => byId.get(s)).filter((p) => p !== undefined);
	if (core.length) {
		out.push('## 最常被查阅：注册、手机验证与付款', '');
		core.forEach((p) => out.push(line(p)));
		out.push('');
	}

	const coreIds = new Set(core.map((p) => p.id));
	const featuredRest = featured.filter((p) => !coreIds.has(p.id));
	if (featuredRest.length) {
		out.push('## 开发者向重点指南', '');
		featuredRest.forEach((p) => out.push(line(p)));
		out.push('');
	}

	const seen = new Set([...coreIds, ...featuredRest.map((p) => p.id)]);
	const cats = [
		...CATEGORY_ORDER.filter((c) => byCategory.has(c)),
		...[...byCategory.keys()].filter((c) => !CATEGORY_ORDER.includes(c)).sort(),
	];
	for (const c of cats) {
		const list = byCategory.get(c)!.filter((p) => !seen.has(p.id));
		if (!list.length) continue;
		out.push(`## ${c}`, '');
		list.slice(0, PER_CATEGORY).forEach((p) => out.push(line(p)));
		if (list.length > PER_CATEGORY) {
			out.push(`- 该分类另有 ${list.length - PER_CATEGORY} 篇，见 ${base}/categories/`);
		}
		out.push('');
	}

	out.push(
		'## 相关服务（YoTradeApi）',
		'',
		'- [美国手机号验证码代收](https://yotradeapi.com/sms): 用于 ChatGPT / OpenAI 注册验证、API key 创建、Codex 登录；¥29.90 一次，支付宝微信付款，收不到自动换号，换号仍失败全额退款。',
		'- [官方订阅代充](https://yotradeapi.com/#sub): 用纯美国信用卡在美区开通 ChatGPT / Claude 官方订阅，开在客人自己的账号上。',
		'- [Claude Team Premium 席位](https://yotradeapi.com/team.html): 自有 Claude Team 组织按席位分配，Premium 席位用量约为个人 Pro 的 6.25 倍。',
		'- [服务说明与价格](https://yotradeapi.com/llms.txt): 主站的完整业务与价格清单。',
		'',
		'## 完整文章列表',
		'',
		`- [站点地图](${base}/sitemap-index.xml): 全部 ${posts.length} 篇文章的 URL 与更新时间`,
		`- [RSS](${base}/rss.xml): 按发布时间倒序`,
		'',
	);

	return new Response(out.join('\n'), {
		headers: {
			'Content-Type': 'text/plain; charset=utf-8',
			'Cache-Control': 'public, max-age=3600',
		},
	});
}
