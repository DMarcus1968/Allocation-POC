/**
 * Custom EPUB parser — no external EPUB library needed.
 * An EPUB is a ZIP containing HTML/XHTML files + metadata.
 */
import JSZip from 'jszip';
import { parseStringPromise } from 'xml2js';
import path from 'path';
import { BookChapter, BookMeta } from '../types/index.js';

interface ManifestItem {
  id: string;
  href: string;
  mediaType: string;
  properties?: string;
}

export async function parseEpub(buffer: Buffer, bookId: string): Promise<BookMeta> {
  const zip = await JSZip.loadAsync(buffer);

  // Step 1: Find the OPF file via META-INF/container.xml
  const containerXml = await zip.file('META-INF/container.xml')?.async('text');
  if (!containerXml) throw new Error('Invalid EPUB: missing META-INF/container.xml');

  const container = await parseStringPromise(containerXml);
  const opfPath = container.container.rootfiles[0].rootfile[0].$['full-path'];
  const opfDir = path.dirname(opfPath);

  // Step 2: Parse the OPF file
  const opfXml = await zip.file(opfPath)?.async('text');
  if (!opfXml) throw new Error(`Invalid EPUB: missing OPF file at ${opfPath}`);

  const opf = await parseStringPromise(opfXml);
  const pkg = opf.package;

  // Extract metadata
  const meta = pkg.metadata[0];
  const title = extractText(meta['dc:title']) || 'Untitled';
  const author = extractText(meta['dc:creator']) || 'Unknown';

  // Build manifest map: id → ManifestItem
  const manifest = new Map<string, ManifestItem>();
  for (const item of pkg.manifest[0].item) {
    manifest.set(item.$.id, {
      id: item.$.id,
      href: item.$.href,
      mediaType: item.$['media-type'],
      properties: item.$.properties,
    });
  }

  // Step 3: Extract cover image
  let coverImage: string | undefined;
  try {
    coverImage = await extractCoverImage(meta, manifest, opfDir, zip);
  } catch {
    // Cover extraction is best-effort
  }

  // Step 4: Read spine (reading order)
  const spineItems: string[] = pkg.spine[0].itemref.map(
    (ref: any) => ref.$.idref
  );

  // Step 4: Extract chapters from spine
  const chapters: BookChapter[] = [];
  for (const itemId of spineItems) {
    const item = manifest.get(itemId);
    if (!item) continue;
    if (!item.mediaType.includes('html')) continue;

    const filePath = opfDir === '.' ? item.href : `${opfDir}/${item.href}`;
    const file = zip.file(filePath) || zip.file(decodeURIComponent(filePath));
    if (!file) continue;

    let html = await file.async('text');

    // Extract the <body> content
    html = extractBody(html);

    // Resolve images: convert relative paths to data URIs
    html = await resolveImages(html, filePath, zip);

    // Extract a title from the chapter content
    const chapterTitle = extractChapterTitle(html, chapters.length + 1);

    chapters.push({ title: chapterTitle, html });
  }

  return { id: bookId, title, author, chapters, coverImage };
}

async function extractCoverImage(
  meta: any,
  manifest: Map<string, ManifestItem>,
  opfDir: string,
  zip: JSZip
): Promise<string | undefined> {
  // Strategy 1: EPUB3 — manifest item with properties="cover-image"
  let coverItem = [...manifest.values()].find(
    item => item.properties?.includes('cover-image')
  );

  // Strategy 2: EPUB2 — <meta name="cover" content="manifest-id"/>
  if (!coverItem && meta.meta) {
    const metas = Array.isArray(meta.meta) ? meta.meta : [meta.meta];
    const coverMeta = metas.find((m: any) => m.$?.name === 'cover');
    if (coverMeta?.$?.content) {
      coverItem = manifest.get(coverMeta.$.content);
    }
  }

  // Strategy 3: manifest item whose ID contains "cover" and is an image
  if (!coverItem) {
    coverItem = [...manifest.values()].find(
      item => item.id.toLowerCase().includes('cover') && item.mediaType.startsWith('image/')
    );
  }

  if (!coverItem) return undefined;

  const coverPath = opfDir === '.' ? coverItem.href : `${opfDir}/${coverItem.href}`;
  const coverFile = zip.file(coverPath) || zip.file(decodeURIComponent(coverPath));
  if (!coverFile) return undefined;

  const coverData = await coverFile.async('base64');
  const ext = path.extname(coverItem.href).toLowerCase();
  const mime =
    ext === '.png' ? 'image/png' :
    ext === '.gif' ? 'image/gif' :
    ext === '.svg' ? 'image/svg+xml' :
    ext === '.webp' ? 'image/webp' :
    'image/jpeg';

  return `data:${mime};base64,${coverData}`;
}

function extractText(field: any): string | undefined {
  if (!field) return undefined;
  const val = field[0];
  if (typeof val === 'string') return val;
  if (val?._ ) return val._;
  return undefined;
}

function extractBody(html: string): string {
  // Get content between <body> tags
  const bodyMatch = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
  if (bodyMatch) return bodyMatch[1].trim();
  return html;
}

function extractChapterTitle(html: string, fallbackIndex: number): string {
  // Try to find h1, h2, or h3
  const match = html.match(/<h[1-3][^>]*>([\s\S]*?)<\/h[1-3]>/i);
  if (match) {
    return match[1].replace(/<[^>]+>/g, '').trim() || `Chapter ${fallbackIndex}`;
  }
  return `Chapter ${fallbackIndex}`;
}

async function resolveImages(
  html: string,
  chapterPath: string,
  zip: JSZip
): Promise<string> {
  const chapterDir = path.dirname(chapterPath);
  const imgRegex = /<img\s+[^>]*src\s*=\s*["']([^"']+)["'][^>]*>/gi;
  const matches = [...html.matchAll(imgRegex)];

  for (const match of matches) {
    const src = match[1];
    if (src.startsWith('data:')) continue;

    // Resolve the relative path
    const imgPath = src.startsWith('/')
      ? src.slice(1)
      : path.normalize(`${chapterDir}/${src}`).replace(/\\/g, '/');

    const imgFile = zip.file(imgPath) || zip.file(decodeURIComponent(imgPath));
    if (!imgFile) continue;

    try {
      const imgData = await imgFile.async('base64');
      const ext = path.extname(src).toLowerCase();
      const mime =
        ext === '.png' ? 'image/png' :
        ext === '.gif' ? 'image/gif' :
        ext === '.svg' ? 'image/svg+xml' :
        ext === '.webp' ? 'image/webp' :
        'image/jpeg';

      html = html.replace(match[0], match[0].replace(src, `data:${mime};base64,${imgData}`));
    } catch {
      // Skip images that can't be resolved
    }
  }

  return html;
}
