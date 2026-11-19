// gta6-meme-x-01 — the hand-in program.
//
// What this program is for
// ------------------------
// The entry in this bounty is a post on X: a GTA 6 meme whose picture
// carries make.fun's ghost, worked into the scene, and whose text
// carries the bounty link, the @makefunai tag and this account's play
// code, telling its readers that people and their AI agents earn real
// money on make.fun. This repository hands that post in. This program
// is the whole of the hand-in machinery: it carries POST.json, the
// small ledger that names the post's address, from the repository root
// to the output directory the house gate reads.
//
// The contract, exactly as the grader runs it
// --------------------------------------------
//   mkdir -p out && MAKEFUN_BOT_DIR=. MAKEFUN_OUTPUT_DIR=out node main.ts
//
// On success the program writes the very same bytes it read to
// <output dir>/POST.json and prints nothing at all: no banner, no log
// line, no farewell. Silence is part of the contract, so the only voice
// this file ever raises is the named woe it reports on its way out when
// something is wrong. Every failure leaves by one named door, with the
// woe's name and a plain detail on stderr and a non-zero exit code.
//
// The program is deterministic on purpose. It opens no socket, reads no
// clock, rolls no dice and touches no file outside the repository root
// it was pointed at and the output directory it was given. Run it twice
// over the same POST.json and the two output files agree byte for byte,
// which is what the house asks of an entry's two runs.
//
// What counts as a well-shaped address
// ------------------------------------
// POST.json must hold one JSON object whose "url" field is a string
// shaped like the address of a post on X:
//
//   https://x.com/<handle>/status/<post id>
//
// The same address on twitter.com is accepted too, since X answers to
// both names and the house reads either. The handle segment and the
// post id segment must each be present; no part of the address may
// carry a blank, a query string or a fragment, because a post's
// address has none of those. The check is a shape check, not a lookup:
// looking the post up is the house's work, not this program's.

import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const LEDGER_FILE_NAME = 'POST.json';
const HAVEN_BOT_FALLBACK = '/bot';
const HAVEN_OUTPUT_FALLBACK = '/output';
const ADDRESS_SCHEME_PREFIX = 'https://';
const ADDRESS_HOSTS_ACCEPTED: readonly string[] = ['x.com', 'twitter.com'];
const ADDRESS_STATUS_SEGMENT = 'status';
const BLANKNESS_PATTERN = /\s/;
const QUERY_FRAGMENT_PATTERN = /[?#]/;

// declareWoe is the one named exit for every failure in this file. It
// speaks the woe's name and its detail to stderr, then ends the process
// with a non-zero code so no caller can mistake the run for a success.
function declareWoe(woeName: string, woeDetail: string): never {
  console.error(`main.ts: ${woeName}: ${woeDetail}`);
  process.exit(1);
}

// resolveHavenDir settles one directory from the environment: the value
// the grader set wins, and a blank or missing value falls back to the
// container's standing place for that directory.
function resolveHavenDir(envKeyName: string, havenFallback: string): string {
  const envRawValue = process.env[envKeyName];
  let havenSettled = havenFallback;
  if (typeof envRawValue === 'string') {
    const envTrimmedValue = envRawValue.trim();
    if (envTrimmedValue.length > 0) {
      havenSettled = envTrimmedValue;
    }
  }
  return havenSettled;
}

// readLedgerBytes brings POST.json in as raw bytes. The bytes matter:
// the output must be the input exactly, so nothing here decodes or
// re-encodes the ledger on its way through.
function readLedgerBytes(ledgerPath: string): Buffer {
  let ledgerBytes: Buffer | null = null;
  try { ledgerBytes = readFileSync(ledgerPath);
  } catch (ledgerReadWoe) {
    declareWoe(
      'PostLedgerUnreadable',
      `POST.json could not be read at ${ledgerPath}: ${(ledgerReadWoe as Error).message}`,
    );
  }
  if (ledgerBytes === null) {
    declareWoe('PostLedgerUnreadable', `POST.json read back empty-handed at ${ledgerPath}`);
  }
  return ledgerBytes as Buffer;
}

// parseLedgerText turns the ledger's bytes into the value they hold.
// Bytes that are not JSON at all fail here, by name, before any shape
// question is asked of them.
function parseLedgerText(ledgerBytes: Buffer): unknown {
  let ledgerValue: unknown = null;
  try { ledgerValue = JSON.parse(ledgerBytes.toString('utf8'));
  } catch (ledgerParseWoe) {
    declareWoe(
      'PostLedgerMalformed',
      `POST.json is not JSON: ${(ledgerParseWoe as Error).message}`,
    );
  }
  return ledgerValue;
}

// pluckPostAddress takes the "url" field out of the parsed ledger. The
// ledger must be one JSON object and the field must be a string; each
// shortfall is its own named woe, so a fix knows where to land.
function pluckPostAddress(ledgerValue: unknown): string {
  if (typeof ledgerValue !== 'object' || ledgerValue === null || Array.isArray(ledgerValue)) {
    declareWoe('PostLedgerMisshapen', 'POST.json must hold one JSON object');
  }
  const ledgerRecord = ledgerValue as Record<string, unknown>;
  const addressCandidate = ledgerRecord['url'];
  if (typeof addressCandidate !== 'string') {
    declareWoe('PostAddressMissing', 'POST.json holds no string "url" field');
  }
  return addressCandidate as string;
}

// verdictOfAddressShape judges the address's shape and answers with a
// verdict word: 'well-shaped' when the address carries the scheme, an
// accepted host, a handle segment, the status segment and a post id
// segment, each clean; or the name of the first shortfall it meets.
function verdictOfAddressShape(addressText: string): string {
  let shapeVerdict = 'well-shaped';
  if (BLANKNESS_PATTERN.test(addressText)) {
    shapeVerdict = 'blankness-astray';
  }
  if (shapeVerdict === 'well-shaped' && QUERY_FRAGMENT_PATTERN.test(addressText)) {
    shapeVerdict = 'query-astray';
  }
  if (shapeVerdict === 'well-shaped' && !addressText.startsWith(ADDRESS_SCHEME_PREFIX)) {
    shapeVerdict = 'scheme-astray';
  }
  if (shapeVerdict === 'well-shaped') {
    const addressRemainder = addressText.slice(ADDRESS_SCHEME_PREFIX.length);
    const addressSegments = addressRemainder.split('/');
    if (addressSegments.length !== 4) {
      shapeVerdict = 'segments-astray';
    }
    if (shapeVerdict === 'well-shaped') {
      const hostSegment = addressSegments[0] as string;
      const handleSegment = addressSegments[1] as string;
      const statusSegment = addressSegments[2] as string;
      const postIdSegment = addressSegments[3] as string;
      if (!ADDRESS_HOSTS_ACCEPTED.includes(hostSegment)) {
        shapeVerdict = 'host-astray';
      }
      if (handleSegment.length === 0) {
        shapeVerdict = 'handle-astray';
      }
      if (statusSegment !== ADDRESS_STATUS_SEGMENT) {
        shapeVerdict = 'status-astray';
      }
      if (postIdSegment.length === 0) {
        shapeVerdict = 'post-id-astray';
      }
    }
  }
  return shapeVerdict;
}

// carryLedgerToOutput is the whole errand: settle the two directories,
// read the ledger, prove its shape, open the output directory and lay
// the ledger's own bytes down inside it. Nothing is printed on the way.
function carryLedgerToOutput(): void {
  const botHavenDir = resolveHavenDir('MAKEFUN_BOT_DIR', HAVEN_BOT_FALLBACK);
  const outputHavenDir = resolveHavenDir('MAKEFUN_OUTPUT_DIR', HAVEN_OUTPUT_FALLBACK);
  const ledgerSourcePath = join(botHavenDir, LEDGER_FILE_NAME);
  const ledgerLandingPath = join(outputHavenDir, LEDGER_FILE_NAME);
  const ledgerBytes = readLedgerBytes(ledgerSourcePath);
  const ledgerValue = parseLedgerText(ledgerBytes);
  const postAddress = pluckPostAddress(ledgerValue);
  const shapeVerdict = verdictOfAddressShape(postAddress);
  if (shapeVerdict !== 'well-shaped') {
    declareWoe(
      'PostAddressMisshapen',
      `the "url" in POST.json is ${shapeVerdict}: ${postAddress}`,
    );
  }
  try { mkdirSync(outputHavenDir, { recursive: true });
  } catch (outputOpenWoe) {
    declareWoe(
      'OutputHavenUnopenable',
      `the output directory ${outputHavenDir} could not be opened: ${(outputOpenWoe as Error).message}`,
    );
  }
  try { writeFileSync(ledgerLandingPath, ledgerBytes);
  } catch (ledgerWriteWoe) {
    declareWoe(
      'PostLedgerUnwritable',
      `POST.json could not be written at ${ledgerLandingPath}: ${(ledgerWriteWoe as Error).message}`,
    );
  }
}

// The errand runs under one last named door: a surprise that escaped
// every named woe above still leaves with a name and a non-zero code,
// never as a bare stack trace and never as a silent half-success.
try { carryLedgerToOutput();
} catch (handInSurpriseWoe) {
  declareWoe(
    'HandInBroke',
    `the hand-in broke in an unnamed way: ${(handInSurpriseWoe as Error).message}`,
  );
}
