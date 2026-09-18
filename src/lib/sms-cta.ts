// 手机验证类文章改挂 yotradeapi.com/sms（美国号验证码代收）的 CTA。
// 这类读者卡在"收不到验证码"这一步，订阅代充的 CTA 对他们不对口。

/** 明确属于手机验证意图的文章（与 tag/keyword 规则取并集） */
const SMS_SLUGS = new Set([
	'cn-chatgpt-register-without-foreign-phone',
	'cn-sms-verification-platform-review',
	'cn-chatgpt-register-error-fix',
	'cn-chatgpt-account-register-full',
	'cn-chatgpt-first-time-cn-guide',
	'cn-chatgpt-login-region-error',
	'cn-chatgpt-account-banned-recovery',
]);

const SMS_TERMS = ['接码', '手机验证', '手机号', '验证码', '短信验证', '虚拟号'];

export function isSmsIntent(slug: string | undefined, tags: string[], keywords: string[]): boolean {
	if (slug && SMS_SLUGS.has(slug)) return true;
	return [...tags, ...keywords].some((t) => SMS_TERMS.some((term) => t.includes(term)));
}

export function smsHref(slug: string | undefined): string {
	return `https://yotradeapi.com/sms?utm_source=blog&utm_medium=cta_sms&utm_content=${slug ?? 'unknown'}`;
}
