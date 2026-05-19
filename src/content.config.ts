import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const blog = defineCollection({
	// Load Markdown and MDX files in the `src/content/blog/` directory.
	loader: glob({ base: './src/content/blog', pattern: '**/*.{md,mdx}' }),
	// Type-check frontmatter using a schema
	schema: ({ image }) =>
		z.object({
			title: z.string().max(80),
			description: z.string().max(180),
			keywords: z.array(z.string()).min(1),
			pubDate: z.coerce.date(),
			updatedDate: z.coerce.date(),
			canonical: z.string().url(),
			heroImage: z.optional(image()),
			tags: z.array(z.string()).min(1),
			category: z.optional(z.string()),
			featured: z.optional(z.boolean()).default(false),
			draft: z.optional(z.boolean()).default(false),
		}),
});

export const collections = { blog };
