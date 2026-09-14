import fs from 'node:fs'
import path from 'node:path'

const repoRoot = path.resolve(process.cwd(), '..')
const appRoot = process.cwd()
const sourcePath = path.join(repoRoot, 'asu_community_council.json')
const outputPath = path.join(appRoot, 'src/data/partners.ts')
const imageOutputRoot = path.join(appRoot, 'public/partner-images')

const partners = JSON.parse(fs.readFileSync(sourcePath, 'utf8'))

const slugify = (value) =>
  value
    .toLowerCase()
    .replace(/&/g, 'and')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')

const normalizeWebsite = (url) => {
  if (url.startsWith('//')) return `https:${url}`
  if (url.startsWith('http:/') && !url.startsWith('http://') && !url.startsWith('https://')) {
    return url.replace('http:/', 'http://')
  }
  return url
}

const getSection = (markdown, heading) => {
  const pattern = new RegExp(`## ${heading}\\n([\\s\\S]*?)(?=\\n## |$)`)
  return markdown.match(pattern)?.[1].trim() ?? ''
}

const getStatus = (markdown) => {
  const statusLine = markdown
    .split('\n')
    .map((line) => line.trim())
    .find((line) => line.includes('FY25') && line.includes('Valley of the Sun United Way'))

  return statusLine ?? 'FY25 Valley of the Sun United Way funded partner status not available.'
}

const parseLeadership = (markdown, orgDir, slug) => {
  const section = getSection(markdown, 'Executive Leadership')
  const rows = section
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.startsWith('|') && !line.includes('---') && !line.includes('Name | Designation'))

  return rows.map((row) => {
    const cells = row
      .split('|')
      .slice(1, -1)
      .map((cell) => cell.trim())
    const photoMatch = cells[2]?.match(/!\[[^\]]*]\(([^)]+)\)/)
    let photo = ''

    if (photoMatch) {
      const source = path.join(orgDir, photoMatch[1])
      const fileName = path.basename(photoMatch[1])
      const destinationDir = path.join(imageOutputRoot, slug)
      const destination = path.join(destinationDir, fileName)

      if (fs.existsSync(source)) {
        fs.mkdirSync(destinationDir, { recursive: true })
        fs.copyFileSync(source, destination)
        photo = `/partner-images/${slug}/${fileName}`
      }
    }

    return {
      name: cells[0] ?? '',
      title: cells[1] ?? '',
      photo,
    }
  })
}

const parseSources = (markdown) =>
  getSection(markdown, 'Sources')
    .split('\n')
    .map((line) => line.replace(/^- /, '').trim())
    .filter(Boolean)

const records = partners.map((partner) => {
  const slug = slugify(partner.organization)
  const matchingDir = fs
    .readdirSync(repoRoot, { withFileTypes: true })
    .find((entry) => entry.isDirectory() && slugify(entry.name) === slug)
  const orgDirName = matchingDir?.name ?? partner.organization
  const orgDir = path.join(repoRoot, orgDirName)
  const markdownPath = path.join(orgDir, `${orgDirName}.md`)
  const markdown = fs.existsSync(markdownPath) ? fs.readFileSync(markdownPath, 'utf8') : ''
  const leadership = parseLeadership(markdown, orgDir, slug)
  const primaryLeader = leadership.find((leader) => leader.name === partner.name) ?? leadership[0]

  return {
    slug,
    organization: partner.organization,
    leader: partner.name,
    position: partner.position,
    website: normalizeWebsite(partner.website),
    funded: /^FY25 funded partner/.test(getStatus(markdown)),
    status: getStatus(markdown),
    about: getSection(markdown, 'About'),
    missionVision: getSection(markdown, 'Mission & Vision'),
    leadership,
    primaryPhoto: primaryLeader?.photo ?? '',
    sources: parseSources(markdown),
    profilePath: `${orgDirName}/${orgDirName}.md`,
  }
})

const output = `export type Leader = {
  name: string
  title: string
  photo: string
}

export type Partner = {
  slug: string
  organization: string
  leader: string
  position: string
  website: string
  funded: boolean
  status: string
  about: string
  missionVision: string
  leadership: Leader[]
  primaryPhoto: string
  sources: string[]
  profilePath: string
}

export const partners: Partner[] = ${JSON.stringify(records, null, 2)}
`

fs.writeFileSync(outputPath, output)
