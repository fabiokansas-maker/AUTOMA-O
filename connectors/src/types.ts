import { z } from "zod";

export const JobSchema = z.object({
  source: z.string(),
  externalId: z.string(),
  title: z.string(),
  company: z.string().optional(),
  location: z.string().optional(),
  remote: z.boolean().optional(),
  salaryMin: z.number().optional(),
  salaryMax: z.number().optional(),
  salaryCurrency: z.string().optional(),
  postedAt: z.string().datetime().optional(),
  url: z.string().url(),
  applyUrl: z.string().url().optional(),
  description: z.string().optional(),
  requirements: z
    .array(z.object({ skill: z.string(), level: z.string().optional(), required: z.boolean().optional() }))
    .optional(),
  raw: z.unknown().optional(),
});

export type Job = z.infer<typeof JobSchema>;

export interface FetchOptions {
  query?: string;
  location?: string;
  since?: Date;
  limit?: number;
}

export interface ApplyPayload {
  jobId: number;            // id no Postgres
  externalId: string;
  url: string;
  applyUrl?: string;
  coverLetter: string;
  cvText?: string;
  cvFileBase64?: string;
  cvFileName?: string;
  candidate: {
    name: string;
    email: string;
    phone?: string;
    city?: string;
  };
}

export interface ApplyResult {
  status: "sent" | "failed" | "external_redirect" | "skipped";
  submittedAt?: string;
  externalApplicationId?: string;
  redirectUrl?: string;
  error?: string;
  notes?: string;
}

export interface Connector {
  source: string;
  fetchJobs(opts: FetchOptions): Promise<Job[]>;
  applyJob?(payload: ApplyPayload): Promise<ApplyResult>;
}
