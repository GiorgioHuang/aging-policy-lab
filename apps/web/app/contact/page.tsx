import type { Metadata } from "next";
import { ContactForm } from "@/components/ContactForm";
import { pageMetadata } from "@/lib/seo";
import {
  GITHUB_PROFILE_URL,
  GITHUB_REPO_URL,
  GITHUB_NEW_ISSUE_URL,
  GITHUB_DISCUSSIONS_URL,
  GITHUB_USER,
} from "@/lib/site";

// Render at request time so the canonical/OG host reflects the runtime SITE_URL.
export const dynamic = "force-dynamic";

export const metadata: Metadata = pageMetadata({
  title: "Contact",
  description:
    "Get in touch with the Canadian Healthy Aging Policy Observatory — publicly via GitHub issues " +
    "and discussions, or privately through the contact form for collaborations and data requests.",
  path: "/contact",
});

export default function ContactPage() {
  return (
    <main className="container about">
      <header>
        <h1>Contact</h1>
        <p className="about-lede">
          The fastest and most transparent way to reach me is on <strong>GitHub</strong> — issues and
          discussions are public, get notified instantly, and keep a durable record. For anything not
          suited to a public thread (collaborations, data requests, sensitive matters), use the
          private form below.
        </p>
      </header>

      <section id="contact" className="about-contact">
        <div className="about-links">
          <a className="btn" href={GITHUB_NEW_ISSUE_URL} target="_blank" rel="noopener noreferrer">
            Open an issue
          </a>
          <a
            className="btn btn-ghost"
            href={GITHUB_DISCUSSIONS_URL}
            target="_blank"
            rel="noopener noreferrer"
          >
            Start a discussion
          </a>
          <a
            className="btn btn-ghost"
            href={GITHUB_PROFILE_URL}
            target="_blank"
            rel="noopener noreferrer"
          >
            @{GITHUB_USER} on GitHub
          </a>
        </div>

        <p className="about-repo">
          Source &amp; methodology:{" "}
          <a href={GITHUB_REPO_URL} target="_blank" rel="noopener noreferrer">
            {GITHUB_REPO_URL.replace("https://", "")}
          </a>
        </p>

        <h2 className="about-form-heading">Send a private message</h2>
        <ContactForm />
      </section>
    </main>
  );
}
