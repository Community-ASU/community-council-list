import fs from 'node:fs'
import path from 'node:path'

const repoRoot = path.resolve(process.cwd(), '..')
const appRoot = process.cwd()
const sourcePath = path.join(repoRoot, 'asu_community_council.json')
const councilDatabasePath = path.join(repoRoot, 'cc-db.csv')
const collaboratoryDatabasePath = path.join(repoRoot, 'cc-db-1.csv')
const outputPath = path.join(appRoot, 'src/data/partners.ts')
const imageOutputRoot = path.join(appRoot, 'public/partner-images')

const organizationsWithoutPublicLeader = new Set(['Greater Phoenix Urban League'])

const partners = JSON.parse(fs.readFileSync(sourcePath, 'utf8'))

const parseCsv = (content) => {
  const rows = []
  let row = []
  let cell = ''
  let inQuotes = false

  for (let index = 0; index < content.length; index += 1) {
    const char = content[index]
    const next = content[index + 1]

    if (char === '"' && inQuotes && next === '"') {
      cell += '"'
      index += 1
    } else if (char === '"') {
      inQuotes = !inQuotes
    } else if (char === ',' && !inQuotes) {
      row.push(cell)
      cell = ''
    } else if ((char === '\n' || char === '\r') && !inQuotes) {
      if (char === '\r' && next === '\n') index += 1
      row.push(cell)
      if (row.some((value) => value.trim())) rows.push(row)
      row = []
      cell = ''
    } else {
      cell += char
    }
  }

  if (cell || row.length) {
    row.push(cell)
    if (row.some((value) => value.trim())) rows.push(row)
  }

  const [headers = [], ...records] = rows

  return records.map((record) =>
    Object.fromEntries(headers.map((header, index) => [header.trim(), record[index]?.trim() ?? ''])),
  )
}

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

const councilRows = fs.existsSync(councilDatabasePath)
  ? parseCsv(fs.readFileSync(councilDatabasePath, 'utf8'))
  : []
const collaboratoryRows = fs.existsSync(collaboratoryDatabasePath)
  ? parseCsv(fs.readFileSync(collaboratoryDatabasePath, 'utf8'))
  : []

const councilRowByLeader = new Map(
  councilRows.map((row) => [
    `${row['First name'] ?? ''} ${row['Last name'] ?? ''}`
      .replace(/\s+/g, ' ')
      .trim()
      .toLowerCase(),
    row,
  ]),
)

const getCouncilRow = (partner) =>
  councilRowByLeader.get(partner.name.replace(/\s+/g, ' ').trim().toLowerCase()) ??
  councilRows.find((row) => slugify(row.Organization ?? '') === slugify(partner.organization)) ??
  null

const getCollaboratoryRow = (partner) =>
  collaboratoryRows.find((row) => slugify(row.Organization ?? '') === slugify(partner.organization)) ??
  collaboratoryRows.find((row) =>
    slugify(`${row['First name'] ?? ''} ${row['Last name'] ?? ''}`) === slugify(partner.name),
  ) ??
  null

const getFirstField = (row, fieldNames) =>
  fieldNames
    .map((fieldName) => row?.[fieldName]?.trim() ?? '')
    .find(Boolean) ?? ''

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
  const councilRow = getCouncilRow(partner)
  const collaboratoryRow = getCollaboratoryRow(partner)
  const slug = slugify(partner.organization)
  const hideLeader = organizationsWithoutPublicLeader.has(partner.organization)
  const matchingDir = fs
    .readdirSync(repoRoot, { withFileTypes: true })
    .find((entry) => entry.isDirectory() && slugify(entry.name) === slug)
  const orgDirName = matchingDir?.name ?? partner.organization
  const orgDir = path.join(repoRoot, orgDirName)
  const markdownPath = path.join(orgDir, `${orgDirName}.md`)
  const markdown = fs.existsSync(markdownPath) ? fs.readFileSync(markdownPath, 'utf8') : ''
  const leadership = hideLeader ? [] : parseLeadership(markdown, orgDir, slug)
  const primaryLeader = leadership.find((leader) => leader.name === partner.name) ?? leadership[0]

  return {
    slug,
    organization: partner.organization,
    leader: hideLeader ? '' : partner.name,
    position: hideLeader ? '' : partner.position,
    website: normalizeWebsite(partner.website),
    funded: /^FY25 funded partner/.test(getStatus(markdown)),
    status: getStatus(markdown),
    about: getSection(markdown, 'About'),
    missionVision: getSection(markdown, 'Mission & Vision'),
    leadership,
    primaryPhoto: primaryLeader?.photo ?? '',
    sources: parseSources(markdown),
    profilePath: `${orgDirName}/${orgDirName}.md`,
    asuAlum: councilRow?.['ASU Alum?'] ?? '',
    asuAlumDetails: councilRow?.['ASU alum details'] ?? '',
    linkedin: (councilRow?.['LinkedIn profile'] ?? '').trim(),
    collaboratory: normalizeWebsite(
      getFirstField(collaboratoryRow, [
        'Collaboratory Profile',
        'Collaboratory profile',
        'Collaboratory Page',
        'Collaboratory page',
        'Collaboratory',
        'Collaboratory URL',
        'Collaboratory url',
      ]),
    ),
    councilNotes: councilRow?.['Edits/Comments'] ?? '',
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
  asuAlum: string
  asuAlumDetails: string
  linkedin: string
  collaboratory: string
  councilNotes: string
}

export const partners: Partner[] = ${JSON.stringify(records, null, 2)}
`

fs.writeFileSync(outputPath, output)
