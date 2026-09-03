// @ts-check

import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';
import { defineConfig } from 'astro/config';

import fs from 'node:fs';
import path from 'node:path';

// 从文章 frontmatter 的 updatedDate（回退 pubDate）建 slug -> lastmod 映射
const BLOG_DIR = './src/content/blog';
const lastmodBySlug = new Map();
for (const file of fs.readdirSync(BLOG_DIR)) {
	if (!/\.mdx?$/.test(file)) continue;
	const raw = fs.readFileSync(path.join(BLOG_DIR, file), 'utf8');
	const fm = raw.split('---')[1] ?? '';
	const pick = (k) => fm.match(new RegExp(`^${k}:\\s*'?([0-9]{4}-[0-9]{2}-[0-9]{2})`, 'm'))?.[1];
	const date = pick('updatedDate') ?? pick('pubDate');
	if (date) {
		lastmodBySlug.set(`/blog/${file.replace(/\.mdx?$/, '')}/`, new Date(date).toISOString());
	}
}

// https://astro.build/config
export default defineConfig({
	site: 'https://blog.yotradeapi.com',
	integrations: [
		mdx(),
		// Bing 是本站主要流量来源，靠 <lastmod> 决定存量页面的重爬优先级。
		// 默认的 sitemap() 不输出 lastmod，1019 个 URL 对爬虫一视同仁。
		sitemap({
			serialize(item) {
				const d = lastmodBySlug.get(new URL(item.url).pathname);
				if (d) item.lastmod = d;
				return item;
			},
		}),
	],
});
