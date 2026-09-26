#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

function parseArgs(argv) {
  const args = { allowStale: false };
  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index];
    if (value === "--allow-stale") {
      args.allowStale = true;
      continue;
    }
    if (!value.startsWith("--")) throw new Error(`Unexpected argument: ${value}`);
    const key = value.slice(2).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
    const next = argv[index + 1];
    if (!next || next.startsWith("--")) throw new Error(`Missing value for ${value}`);
    args[key] = next;
    index += 1;
  }
  for (const required of ["sourceRepo", "targetRepo", "couponExport"]) {
    if (!args[required]) {
      const flag = required.replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`);
      throw new Error(`Missing --${flag}`);
    }
  }
  return args;
}

function berlinDateStamp(date = new Date()) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Berlin",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function walkYaml(directory) {
  const files = [];
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const child = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...walkYaml(child));
    else if (entry.isFile() && entry.name.endsWith(".yaml") && entry.name !== "_schema.yaml") files.push(child);
  }
  return files.sort();
}

function haversineKm(a, b) {
  const toRad = (value) => (value * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const lat1 = toRad(a.lat);
  const lat2 = toRad(b.lat);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(h));
}

function merchantRefs(coupon) {
  const refs = [{
    catalogId: coupon.merchantRestaurantCatalogId || null,
    catalogSlug: coupon.merchantRestaurantCatalogSlug || null,
    merchantName: coupon.merchantName || null,
    role: "primary",
  }];
  for (const item of Array.isArray(coupon.applicableMerchantNames) ? coupon.applicableMerchantNames : []) {
    refs.push({
      catalogId: item.restaurantCatalogId || null,
      catalogSlug: item.restaurantCatalogSlug || null,
      merchantName: item.merchantName || null,
      role: "applicable",
    });
  }
  return refs.filter((ref) => ref.catalogId || ref.catalogSlug);
}

function couponSummary(coupon) {
  return {
    id: coupon.id,
    expiresOn: coupon.expiresOn,
    shortOffer: coupon.shortOffer || null,
    description: coupon.description || null,
  };
}

function normalizedNames(...values) {
  const flattened = values.flatMap((value) => {
    if (typeof value === "string") return [value];
    if (Array.isArray(value)) return value;
    if (value && typeof value === "object") return Object.values(value);
    return [];
  });
  return new Set(flattened
    .filter((value) => typeof value === "string")
    .map((value) => value.normalize("NFKC").toLowerCase().replace(/[^\p{L}\p{N}]+/gu, "").trim())
    .filter((value) => value.length >= 2));
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const sourceRepo = path.resolve(args.sourceRepo);
  const targetRepo = path.resolve(args.targetRepo);
  const exportPath = path.resolve(args.couponExport);
  const targetPackage = path.join(targetRepo, "scripts", "sync-to-firestore", "package.json");
  const requireFromTarget = createRequire(targetPackage);
  let yaml;
  try {
    yaml = requireFromTarget("js-yaml");
  } catch {
    throw new Error(`Cannot load js-yaml. Run npm ci in ${path.dirname(targetPackage)} first.`);
  }

  const snapshot = readJson(exportPath);
  const today = berlinDateStamp();
  if (!args.allowStale && snapshot.validOn !== today) {
    throw new Error(`Coupon export is stale: validOn=${snapshot.validOn || "missing"}, Berlin today=${today}`);
  }
  const coupons = Array.isArray(snapshot.coupons) ? snapshot.coupons : [];

  const sourcePackets = new Map();
  const sourceDir = path.join(sourceRepo, "data", "restaurants");
  for (const file of fs.readdirSync(sourceDir).filter((name) => name.endsWith("__source-packet.json"))) {
    const packet = readJson(path.join(sourceDir, file));
    if (packet.packet_meta?.packetId) sourcePackets.set(packet.packet_meta.packetId, packet);
  }

  const targetRoot = path.join(targetRepo, "data", "restaurants");
  const targets = walkYaml(targetRoot).map((file) => {
    const data = yaml.load(fs.readFileSync(file, "utf8")) || {};
    return {
      id: path.basename(file, ".yaml"),
      path: path.relative(targetRepo, file),
      data,
      names: normalizedNames(data.name),
      placeId: typeof data.placeId === "string" ? data.placeId : null,
      geo: Number.isFinite(data.latitude) && Number.isFinite(data.longitude)
        ? { lat: data.latitude, lng: data.longitude }
        : null,
    };
  });
  const targetById = new Map(targets.map((target) => [target.id, target]));
  const targetByPlaceId = new Map(targets.filter((target) => target.placeId).map((target) => [target.placeId, target]));

  const groups = new Map();
  for (const coupon of coupons) {
    for (const ref of merchantRefs(coupon)) {
      const key = ref.catalogId || `slug:${ref.catalogSlug}`;
      if (!groups.has(key)) groups.set(key, { ...ref, coupons: [] });
      const group = groups.get(key);
      if (!group.coupons.some((item) => item.id === coupon.id)) group.coupons.push(couponSummary(coupon));
    }
  }

  function matchGroup(group) {
    const slug = group.catalogSlug || group.catalogId?.replace(/^berlin__/, "") || null;
    if (slug && targetById.has(slug)) return { target: targetById.get(slug), method: "exact_target_id" };
    const packet = group.catalogId ? sourcePackets.get(group.catalogId) : null;
    const placeId = packet?.identity?.placeId;
    if (placeId && targetByPlaceId.has(placeId)) return { target: targetByPlaceId.get(placeId), method: "exact_place_id" };
    const sourceNames = normalizedNames(
      group.merchantName,
      packet?.identity?.canonicalName,
      packet?.identity?.aliases,
      packet?.seed?.nameZh,
      packet?.seed?.nameEn,
      packet?.seed?.nameDe,
    );
    const nameMatches = targets.filter((target) => [...sourceNames].some((name) => target.names.has(name)));
    if (nameMatches.length === 1) return { target: nameMatches[0], method: "unique_exact_name" };
    const sourceGeo = packet?.identity?.geo;
    if (Number.isFinite(sourceGeo?.lat) && Number.isFinite(sourceGeo?.lng)) {
      const nearby = targets
        .filter((target) => target.geo)
        .map((target) => ({ target, distanceKm: haversineKm(sourceGeo, target.geo) }))
        .filter((item) => item.distanceKm <= 0.1)
        .sort((a, b) => a.distanceKm - b.distanceKm);
      return {
        target: null,
        method: nearby.length > 0 ? "coordinate_candidate_requires_review" : "unmatched",
        coordinateCandidates: nearby.slice(0, 3).map((item) => ({
          targetPath: item.target.path,
          targetId: item.target.id,
          targetName: item.target.data.name || null,
          distanceMeters: Math.round(item.distanceKm * 1000),
        })),
      };
    }
    return { target: null, method: "unmatched" };
  }

  const matched = [];
  const unmatched = [];
  const activeTargetPaths = new Set();
  for (const group of groups.values()) {
    const match = matchGroup(group);
    const row = {
      catalogId: group.catalogId,
      catalogSlug: group.catalogSlug,
      merchantName: group.merchantName,
      coupons: group.coupons.sort((a, b) => a.id.localeCompare(b.id)),
      matchMethod: match.method,
      distanceMeters: match.distanceKm === undefined ? null : Math.round(match.distanceKm * 1000),
      coordinateCandidates: match.coordinateCandidates || [],
      targetPath: match.target?.path || null,
      targetId: match.target?.id || null,
      targetHasDiscount: match.target?.data?.hasDiscount === true,
      targetDiscountInfo: match.target?.data?.discountInfo || null,
    };
    if (!match.target) unmatched.push(row);
    else {
      activeTargetPaths.add(match.target.path);
      matched.push(row);
    }
  }

  const activate = matched.filter((row) => !row.targetHasDiscount);
  const keep = matched.filter((row) => row.targetHasDiscount);
  const deactivate = targets
    .filter((target) => target.data.hasDiscount === true && !activeTargetPaths.has(target.path))
    .map((target) => ({ targetPath: target.path, targetId: target.id, targetDiscountInfo: target.data.discountInfo || null }));

  process.stdout.write(`${JSON.stringify({
    generatedAt: new Date().toISOString(),
    berlinDate: today,
    couponExport: exportPath,
    exportValidOn: snapshot.validOn || null,
    coupons: coupons.length,
    activeMerchantGroups: groups.size,
    targetRestaurants: targets.length,
    counts: { activate: activate.length, keep: keep.length, deactivate: deactivate.length, unmatched: unmatched.length },
    activate,
    keep,
    deactivate,
    unmatched,
  }, null, 2)}\n`);
}

try {
  main();
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
}
