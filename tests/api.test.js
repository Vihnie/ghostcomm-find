import assert from 'node:assert/strict'
import test from 'node:test'
import { ApiError, createApi } from '../src/api.js'

test('JSON requests use the API prefix and bearer authentication', async () => {
  const api = createApi('test-token', undefined, async (url, options) => {
    assert.equal(url, '/api/v1/items')
    assert.equal(options.headers.get('Authorization'), 'Bearer test-token')
    assert.equal(options.headers.get('Content-Type'), 'application/json')
    assert.deepEqual(JSON.parse(options.body), { title: 'Campus bag' })
    return new Response(JSON.stringify({ id: 'item-id' }), { status: 201 })
  })
  assert.deepEqual(await api('/items', { method: 'POST', body: { title: 'Campus bag' } }), { id: 'item-id' })
})

test('OAuth login sends form data rather than JSON', async () => {
  const body = new URLSearchParams({ username: 'student@example.com', password: 'test-password' })
  const api = createApi('', undefined, async (_url, options) => {
    assert.equal(options.body, body)
    assert.equal(options.headers.has('Content-Type'), false)
    assert.equal(options.headers.has('Authorization'), false)
    return new Response(JSON.stringify({ access_token: 'test-token' }))
  })
  assert.equal((await api('/auth/login', { method: 'POST', body })).access_token, 'test-token')
})

test('multipart upload leaves the boundary to the browser', async () => {
  const body = new FormData()
  body.set('file', new Blob(['file contents']), 'photo.png')
  const api = createApi('test-token', undefined, async (_url, options) => {
    assert.equal(options.body, body)
    assert.equal(options.headers.has('Content-Type'), false)
    return new Response(JSON.stringify({ id: 'file-id' }), { status: 201 })
  })
  assert.equal((await api('/items/item-id/media', { method: 'POST', body })).id, 'file-id')
})

test('expired authentication notifies the session and surfaces the error', async () => {
  let expired = false
  const api = createApi('expired-token', () => { expired = true }, async () => new Response(
    JSON.stringify({ detail: 'Invalid or expired token' }), { status: 401 },
  ))
  await assert.rejects(api('/auth/me'), error => error instanceof ApiError && error.status === 401)
  assert.equal(expired, true)
})

test('validation errors include the failing field', async () => {
  const api = createApi('', undefined, async () => new Response(JSON.stringify({
    detail: [{ loc: ['body', 'description'], msg: 'String should have at least 10 characters' }],
  }), { status: 422 }))
  await assert.rejects(api('/items'), /description: String should have at least 10 characters/)
})

test('downloads return blobs and deletion accepts an empty response', async () => {
  const api = createApi('', undefined, async (_url, options) => options.method === 'DELETE'
    ? new Response(null, { status: 204 }) : new Response('image contents'))
  assert.equal(await (await api('/media/file-id', { blob: true })).text(), 'image contents')
  assert.equal(await api('/media/file-id', { method: 'DELETE' }), null)
})

test('network failures are explained without leaking credentials', async () => {
  const api = createApi('private-token', undefined, async () => { throw new Error('network failed') })
  await assert.rejects(api('/items'), /Cannot reach the server/)
})

test('unconfigured AI shows a user-facing message', async () => {
  const api = createApi('test-token', undefined, async () => new Response(JSON.stringify({
    detail: 'AI is not configured. Set GEMINI_API_KEY on the server',
  }), { status: 503 }))
  await assert.rejects(api('/items/item-id/matches', { method: 'POST' }), error =>
    error.status === 503 && error.message.includes('You can still search reports') &&
    !error.message.includes('GEMINI_API_KEY'))
})
