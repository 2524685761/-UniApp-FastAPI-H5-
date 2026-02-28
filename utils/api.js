const DEFAULT_BASE_URL = 'http://127.0.0.1:8000'
const USER_ID_KEY = 'user_id'
const DEFAULT_USER_ID = 1

// ============ 基础URL管理 ============

export function normalizeBaseURL(url) {
	if (!url) return DEFAULT_BASE_URL
	let u = String(url).trim()
	// 允许用户只填 127.0.0.1:8000 这种
	if (!/^https?:\/\//i.test(u)) {
		u = 'http://' + u
	}
	// 去掉末尾 /
	u = u.replace(/\/+$/, '')
	return u
}

export function getBaseURL() {
	const saved = uni.getStorageSync('api_base_url')
	return normalizeBaseURL(saved || DEFAULT_BASE_URL)
}

export function setBaseURL(url) {
	const u = normalizeBaseURL(url)
	uni.setStorageSync('api_base_url', u)
	return u
}

export function buildURL(path) {
	if (!path) return getBaseURL()
	const p = String(path)
	if (/^https?:\/\//i.test(p)) return p
	if (!p.startsWith('/')) return getBaseURL() + '/' + p
	return getBaseURL() + p
}

export function getUserId() {
	const raw = uni.getStorageSync(USER_ID_KEY)
	const n = Number(raw)
	if (Number.isFinite(n) && n > 0) return Math.floor(n)
	uni.setStorageSync(USER_ID_KEY, DEFAULT_USER_ID)
	return DEFAULT_USER_ID
}

export function setUserId(userId) {
	const n = Number(userId)
	const safeId = Number.isFinite(n) && n > 0 ? Math.floor(n) : DEFAULT_USER_ID
	uni.setStorageSync(USER_ID_KEY, safeId)
	return safeId
}

// ============ 统一请求封装 ============

/**
 * 统一的请求配置
 */
const REQUEST_CONFIG = {
	timeout: 30000,
	retryCount: 1,
	retryDelay: 1000
}

/**
 * 统一错误处理
 * @param {Error|Object} error - 错误对象
 * @param {string} context - 错误上下文描述
 * @returns {string} 用户友好的错误信息
 */
function handleError(error, context = '') {
	console.error(`[API Error] ${context}:`, error)
	
	// 网络错误
	if (error.errMsg && error.errMsg.includes('fail')) {
		if (error.errMsg.includes('timeout')) {
			return '请求超时，请检查网络后重试'
		}
		return '网络连接失败，请检查后端服务是否启动'
	}
	
	// HTTP错误
	if (error.statusCode) {
		const status = error.statusCode
		if (status === 400) return '请求参数错误'
		if (status === 404) return '接口不存在'
		if (status === 500) return '服务器内部错误'
		return `请求失败 (${status})`
	}
	
	// 其他错误
	return error.message || '未知错误'
}

/**
 * 显示错误提示
 * @param {string} message - 错误信息
 * @param {number} duration - 显示时长
 */
function showError(message, duration = 2500) {
	uni.showToast({
		title: message,
		icon: 'none',
		duration
	})
}

/**
 * 统一GET请求
 * @param {string} path - 请求路径
 * @param {Object} options - 可选配置
 * @returns {Promise<any>} 响应数据
 */
export function apiGet(path, options = {}) {
	const { showLoading = false, loadingText = '加载中...', silent = false } = options
	
	return new Promise((resolve, reject) => {
		if (showLoading) {
			uni.showLoading({ title: loadingText })
		}
		
		uni.request({
			url: buildURL(path),
			method: 'GET',
			timeout: REQUEST_CONFIG.timeout,
			success: (res) => {
				if (res.statusCode === 200) {
					resolve(res.data)
				} else {
					const errMsg = handleError({ statusCode: res.statusCode }, path)
					if (!silent) showError(errMsg)
					reject(new Error(errMsg))
				}
			},
			fail: (err) => {
				const errMsg = handleError(err, path)
				if (!silent) showError(errMsg)
				reject(new Error(errMsg))
			},
			complete: () => {
				if (showLoading) uni.hideLoading()
			}
		})
	})
}

/**
 * 统一POST请求
 * @param {string} path - 请求路径
 * @param {Object} data - 请求数据
 * @param {Object} options - 可选配置
 * @returns {Promise<any>} 响应数据
 */
export function apiPost(path, data = {}, options = {}) {
	const { showLoading = false, loadingText = '处理中...', silent = false } = options
	
	return new Promise((resolve, reject) => {
		if (showLoading) {
			uni.showLoading({ title: loadingText })
		}
		
		uni.request({
			url: buildURL(path),
			method: 'POST',
			data,
			timeout: REQUEST_CONFIG.timeout,
			header: { 'Content-Type': 'application/json' },
			success: (res) => {
				if (res.statusCode === 200) {
					resolve(res.data)
				} else {
					const errMsg = handleError({ statusCode: res.statusCode }, path)
					if (!silent) showError(errMsg)
					reject(new Error(errMsg))
				}
			},
			fail: (err) => {
				const errMsg = handleError(err, path)
				if (!silent) showError(errMsg)
				reject(new Error(errMsg))
			},
			complete: () => {
				if (showLoading) uni.hideLoading()
			}
		})
	})
}

/**
 * 统一文件上传
 * @param {string} path - 上传路径
 * @param {string} filePath - 本地文件路径
 * @param {Object} formData - 额外表单数据
 * @param {Object} options - 可选配置
 * @returns {Promise<any>} 响应数据
 */
export function apiUpload(path, filePath, formData = {}, options = {}) {
	const { 
		showLoading = true, 
		loadingText = '上传中...', 
		silent = false,
		fileName = 'file'
	} = options
	
	return new Promise((resolve, reject) => {
		if (showLoading) {
			uni.showLoading({ title: loadingText })
		}
		
		uni.uploadFile({
			url: buildURL(path),
			filePath,
			name: fileName,
			formData,
			success: (res) => {
				if (res.statusCode === 200) {
					try {
						const data = JSON.parse(res.data)
						resolve(data)
					} catch (e) {
						const errMsg = '响应数据解析失败'
						if (!silent) showError(errMsg)
						reject(new Error(errMsg))
					}
				} else {
					const errMsg = handleError({ statusCode: res.statusCode }, path)
					if (!silent) showError(errMsg)
					reject(new Error(errMsg))
				}
			},
			fail: (err) => {
				const errMsg = handleError(err, path)
				if (!silent) showError(errMsg)
				reject(new Error(errMsg))
			},
			complete: () => {
				if (showLoading) uni.hideLoading()
			}
		})
	})
}

/**
 * H5环境 Fetch 上传（支持FormData）
 * 支持多平台兼容
 * @param {string} path - 上传路径
 * @param {FormData} formData - FormData对象
 * @param {Object} options - 可选配置
 * @returns {Promise<any>} 响应数据
 */
export async function apiFetch(path, formData, options = {}) {
	const { 
		showLoading = true, 
		loadingText = '处理中...', 
		silent = false,
		timeout = REQUEST_CONFIG.timeout,
		retryCount = 2  // 新增: 重试次数
	} = options
	
	if (showLoading) {
		uni.showLoading({ title: loadingText })
	}
	
	let lastError = null
	
	// 重试机制
	for (let attempt = 0; attempt <= retryCount; attempt++) {
		try {
			// 超时控制
			const controller = new AbortController()
			const timeoutId = setTimeout(() => controller.abort(), timeout)
			
			const response = await fetch(buildURL(path), {
				method: 'POST',
				body: formData,
				signal: controller.signal
			})
			
			clearTimeout(timeoutId)
			
			if (!response.ok) {
				const text = await response.text()
				throw new Error(`HTTP ${response.status}: ${text}`)
			}
			
			const data = await response.json()
			return data
			
		} catch (err) {
			lastError = err
			
			// 如果是超时或网络错误，等待后重试
			if (attempt < retryCount && (err.name === 'AbortError' || err.message.includes('network'))) {
				await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)))
				continue
			}
			break
		}
	}
	
	// 所有重试都失败
	let errMsg = '请求失败'
	if (lastError.name === 'AbortError') {
		errMsg = '请求超时，请重试'
	} else {
		errMsg = lastError.message || '未知错误'
	}
	
	if (!silent) showError(errMsg, 3000)
	if (showLoading) uni.hideLoading()
	throw new Error(errMsg)
	
}

// ============ 业务API封装 ============

/**
 * 获取课程列表
 */
export function fetchCourses() {
	return apiGet('/courses', { silent: true })
}

/**
 * 获取用户统计信息
 */
export function fetchStats() {
	return apiGet(`/stats?user_id=${getUserId()}`, { silent: true })
}

/**
 * 获取情绪周报
 */
export function fetchMoodWeekly() {
	return apiGet(`/mood/weekly?user_id=${getUserId()}`, { silent: true })
}

/**
 * 获取薄弱词汇
 */
export function fetchWeakWords(limit = 50) {
	return apiGet(`/weak_words?user_id=${getUserId()}&limit=${limit}`, { silent: true })
}

/**
 * 鑾峰彇瀛︿範璁板綍
 */
export function fetchRecords(limit = 50) {
	return apiGet(`/records?user_id=${getUserId()}&limit=${limit}`, { silent: true })
}

/**
 * 获取随机故事
 */
export function fetchStory(category = null) {
	const path = category ? `/chat/story?category=${category}` : '/chat/story'
	return apiGet(path, { showLoading: true, loadingText: '故事准备中...' })
}

/**
 * 获取故事分类列表
 */
export function fetchStoryCategories() {
	return apiGet('/chat/categories', { silent: true })
}

/**
 * 测试后端连接
 */
export async function testConnection() {
	try {
		await apiGet('/courses', { silent: true })
		return { success: true, message: '连接成功' }
	} catch (err) {
		return { success: false, message: err.message }
	}
}

// 默认导出对象（兼容不同调用方式）
export default {
	getBaseUrl: getBaseURL,
	setBaseUrl: setBaseURL,
	buildUrl: buildURL,
	normalizeBaseUrl: normalizeBaseURL,
	getUserId,
	setUserId,
	// 新增统一请求方法
	get: apiGet,
	post: apiPost,
	upload: apiUpload,
	fetch: apiFetch,
	// 业务API
	fetchCourses,
	fetchStats,
	fetchMoodWeekly,
	fetchWeakWords,
	fetchRecords,
	fetchStory,
	testConnection
}


