import { z } from "zod";

export const SearchResult = z.object({
  id: z.string(),
  title: z.string().optional(),
  text: z.string(),
  snippet: z.string().optional(),
  tags: z.array(z.string()).optional(),
  meta: z.object({
    vendor_name: z.string().optional(),
    meeting_date: z.string().optional(),
    doc_type: z.string().optional()
  }).passthrough()
});
export type SearchResult = z.infer<typeof SearchResult>;

export const SearchResponse = z.object({
  query: z.string(),
  results: z.array(SearchResult)
});
export type SearchResponse = z.infer<typeof SearchResponse>;

export type SearchFilters = { vendor?: string; from?: string; to?: string; };
