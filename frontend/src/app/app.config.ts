import { ApplicationConfig } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { LucideAngularModule, LogIn, LogOut, Users, ClipboardList, Swords, DoorOpen, Wallet, Search, UserPlus, ShieldCheck, ShieldAlert, Play, Square, Clock, Pencil, Save, X, TrendingUp, CalendarClock, Check, AlertTriangle, Target, Award, StickyNote, Menu, Info } from 'lucide-angular';
import { importProvidersFrom } from '@angular/core';

import { routes } from './app.routes';
import { authInterceptor } from './services/auth.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    provideHttpClient(withInterceptors([authInterceptor])),
    // Registra os ícones Lucide usados na aplicação (tree-shakeable).
    importProvidersFrom(
      LucideAngularModule.pick({
        LogIn,
        LogOut,
        Users,
        ClipboardList,
        Swords,
        DoorOpen,
        Wallet,
        Search,
        UserPlus,
        ShieldCheck,
        ShieldAlert,
        Play,
        Square,
        Clock,
        Pencil,
        Save,
        X,
        TrendingUp,
        CalendarClock,
        Check,
        AlertTriangle,
        Target,
        Award,
        StickyNote,
        Menu,
        Info,
      })
    ),
  ],
};
