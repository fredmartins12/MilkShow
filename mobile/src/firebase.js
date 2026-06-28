import { initializeApp, getApps } from 'firebase/app'
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  sendPasswordResetEmail,
  signOut as firebaseSignOut,
} from 'firebase/auth'

const firebaseConfig = {
  apiKey:    'AIzaSyCViWGZK5jySuerObH6jjHoNXyobbxQDVs',
  authDomain: 'gestaodeleite-52cf2.firebaseapp.com',
  projectId:  'gestaodeleite-52cf2',
}

const app  = getApps().length ? getApps()[0] : initializeApp(firebaseConfig)
const auth = getAuth(app)

/** Login com Google — retorna Firebase ID token */
export async function signInWithGoogle() {
  const provider = new GoogleAuthProvider()
  const result   = await signInWithPopup(auth, provider)
  return result.user.getIdToken()
}

/** Login com Email + Senha — retorna Firebase ID token */
export async function signInWithEmail(email, password) {
  const result = await signInWithEmailAndPassword(auth, email, password)
  return result.user.getIdToken()
}

/** Criar conta com Email + Senha — retorna Firebase ID token */
export async function createAccountWithEmail(email, password) {
  const result = await createUserWithEmailAndPassword(auth, email, password)
  return result.user.getIdToken()
}

/** Envia email de redefinição de senha */
export async function resetPassword(email) {
  await sendPasswordResetEmail(auth, email)
}

/** Logout do Firebase */
export async function signOut() {
  await firebaseSignOut(auth)
}
