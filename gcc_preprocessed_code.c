void DCEMarker0_(void);
void DCEMarker1_(void);
void DCEMarker2_(void);
void DCEMarker3_(void);
void DCEMarker4_(void);
void DCEMarker5_(void);
void DCEMarker6_(void);
void DCEMarker7_(void);
void DCEMarker8_(void);
void DCEMarker9_(void);
void DCEMarker10_(void);
void DCEMarker11_(void);
void DCEMarker12_(void);
void DCEMarker13_(void);
void DCEMarker14_(void);
void DCEMarker15_(void);
void DCEMarker16_(void);
void DCEMarker17_(void);
void DCEMarker18_(void);
void DCEMarker19_(void);
void DCEMarker20_(void);
void DCEMarker21_(void);
void DCEMarker22_(void);
void DCEMarker23_(void);
void DCEMarker24_(void);
void DCEMarker25_(void);
void DCEMarker26_(void);
void DCEMarker27_(void);
void DCEMarker28_(void);
void DCEMarker29_(void);
void DCEMarker30_(void);

typedef long unsigned int size_t;
extern void *memcpy (void *__restrict __dest, const void *__restrict __src,
       size_t __n) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern void *memmove (void *__dest, const void *__src, size_t __n)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern void *memccpy (void *__restrict __dest, const void *__restrict __src,
        int __c, size_t __n)
    __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2))) __attribute__ ((__access__ (__write_only__, 1, 4)));
extern void *memset (void *__s, int __c, size_t __n) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern int memcmp (const void *__s1, const void *__s2, size_t __n)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));
extern int __memcmpeq (const void *__s1, const void *__s2, size_t __n)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));
extern void *memchr (const void *__s, int __c, size_t __n)
      __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1)));
extern char *strcpy (char *__restrict __dest, const char *__restrict __src)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern char *strncpy (char *__restrict __dest,
        const char *__restrict __src, size_t __n)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern char *strcat (char *__restrict __dest, const char *__restrict __src)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern char *strncat (char *__restrict __dest, const char *__restrict __src,
        size_t __n) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern int strcmp (const char *__s1, const char *__s2)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));
extern int strncmp (const char *__s1, const char *__s2, size_t __n)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));
extern int strcoll (const char *__s1, const char *__s2)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));
extern size_t strxfrm (char *__restrict __dest,
         const char *__restrict __src, size_t __n)
    __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2))) __attribute__ ((__access__ (__write_only__, 1, 3)));
struct __locale_struct
{
  struct __locale_data *__locales[13];
  const unsigned short int *__ctype_b;
  const int *__ctype_tolower;
  const int *__ctype_toupper;
  const char *__names[13];
};
typedef struct __locale_struct *__locale_t;
typedef __locale_t locale_t;
extern int strcoll_l (const char *__s1, const char *__s2, locale_t __l)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2, 3)));
extern size_t strxfrm_l (char *__dest, const char *__src, size_t __n,
    locale_t __l) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2, 4)))
     __attribute__ ((__access__ (__write_only__, 1, 3)));
extern char *strdup (const char *__s)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__malloc__)) __attribute__ ((__nonnull__ (1)));
extern char *strndup (const char *__string, size_t __n)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__malloc__)) __attribute__ ((__nonnull__ (1)));
extern char *strchr (const char *__s, int __c)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1)));
extern char *strrchr (const char *__s, int __c)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1)));
extern size_t strcspn (const char *__s, const char *__reject)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));
extern size_t strspn (const char *__s, const char *__accept)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));
extern char *strpbrk (const char *__s, const char *__accept)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));
extern char *strstr (const char *__haystack, const char *__needle)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));
extern char *strtok (char *__restrict __s, const char *__restrict __delim)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2)));
extern char *__strtok_r (char *__restrict __s,
    const char *__restrict __delim,
    char **__restrict __save_ptr)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2, 3)));
extern char *strtok_r (char *__restrict __s, const char *__restrict __delim,
         char **__restrict __save_ptr)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2, 3)));
extern size_t strlen (const char *__s)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1)));
extern size_t strnlen (const char *__string, size_t __maxlen)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1)));
extern char *strerror (int __errnum) __attribute__ ((__nothrow__ , __leaf__));
extern int strerror_r (int __errnum, char *__buf, size_t __buflen) __asm__ ("" "__xpg_strerror_r") __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2)))
    __attribute__ ((__access__ (__write_only__, 2, 3)));
extern char *strerror_l (int __errnum, locale_t __l) __attribute__ ((__nothrow__ , __leaf__));

extern int bcmp (const void *__s1, const void *__s2, size_t __n)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));
extern void bcopy (const void *__src, void *__dest, size_t __n)
  __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern void bzero (void *__s, size_t __n) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern char *index (const char *__s, int __c)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1)));
extern char *rindex (const char *__s, int __c)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1)));
extern int ffs (int __i) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern int ffsl (long int __l) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
__extension__ extern int ffsll (long long int __ll)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern int strcasecmp (const char *__s1, const char *__s2)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));
extern int strncasecmp (const char *__s1, const char *__s2, size_t __n)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));
extern int strcasecmp_l (const char *__s1, const char *__s2, locale_t __loc)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2, 3)));
extern int strncasecmp_l (const char *__s1, const char *__s2,
     size_t __n, locale_t __loc)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2, 4)));

extern void explicit_bzero (void *__s, size_t __n) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)))
    __attribute__ ((__access__ (__write_only__, 1, 2)));
extern char *strsep (char **__restrict __stringp,
       const char *__restrict __delim)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern char *strsignal (int __sig) __attribute__ ((__nothrow__ , __leaf__));
extern char *__stpcpy (char *__restrict __dest, const char *__restrict __src)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern char *stpcpy (char *__restrict __dest, const char *__restrict __src)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern char *__stpncpy (char *__restrict __dest,
   const char *__restrict __src, size_t __n)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern char *stpncpy (char *__restrict __dest,
        const char *__restrict __src, size_t __n)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));


typedef unsigned char __u_char;
typedef unsigned short int __u_short;
typedef unsigned int __u_int;
typedef unsigned long int __u_long;
typedef signed char __int8_t;
typedef unsigned char __uint8_t;
typedef signed short int __int16_t;
typedef unsigned short int __uint16_t;
typedef signed int __int32_t;
typedef unsigned int __uint32_t;
typedef signed long int __int64_t;
typedef unsigned long int __uint64_t;
typedef __int8_t __int_least8_t;
typedef __uint8_t __uint_least8_t;
typedef __int16_t __int_least16_t;
typedef __uint16_t __uint_least16_t;
typedef __int32_t __int_least32_t;
typedef __uint32_t __uint_least32_t;
typedef __int64_t __int_least64_t;
typedef __uint64_t __uint_least64_t;
typedef long int __quad_t;
typedef unsigned long int __u_quad_t;
typedef long int __intmax_t;
typedef unsigned long int __uintmax_t;
typedef unsigned long int __dev_t;
typedef unsigned int __uid_t;
typedef unsigned int __gid_t;
typedef unsigned long int __ino_t;
typedef unsigned long int __ino64_t;
typedef unsigned int __mode_t;
typedef unsigned long int __nlink_t;
typedef long int __off_t;
typedef long int __off64_t;
typedef int __pid_t;
typedef struct { int __val[2]; } __fsid_t;
typedef long int __clock_t;
typedef unsigned long int __rlim_t;
typedef unsigned long int __rlim64_t;
typedef unsigned int __id_t;
typedef long int __time_t;
typedef unsigned int __useconds_t;
typedef long int __suseconds_t;
typedef long int __suseconds64_t;
typedef int __daddr_t;
typedef int __key_t;
typedef int __clockid_t;
typedef void * __timer_t;
typedef long int __blksize_t;
typedef long int __blkcnt_t;
typedef long int __blkcnt64_t;
typedef unsigned long int __fsblkcnt_t;
typedef unsigned long int __fsblkcnt64_t;
typedef unsigned long int __fsfilcnt_t;
typedef unsigned long int __fsfilcnt64_t;
typedef long int __fsword_t;
typedef long int __ssize_t;
typedef long int __syscall_slong_t;
typedef unsigned long int __syscall_ulong_t;
typedef __off64_t __loff_t;
typedef char *__caddr_t;
typedef long int __intptr_t;
typedef unsigned int __socklen_t;
typedef int __sig_atomic_t;
typedef float float_t;
typedef double double_t;
extern int __fpclassify (double __value) __attribute__ ((__nothrow__ , __leaf__))
     __attribute__ ((__const__));
extern int __signbit (double __value) __attribute__ ((__nothrow__ , __leaf__))
     __attribute__ ((__const__));
extern int __isinf (double __value) __attribute__ ((__nothrow__ , __leaf__))
  __attribute__ ((__const__));
extern int __finite (double __value) __attribute__ ((__nothrow__ , __leaf__))
  __attribute__ ((__const__));
extern int __isnan (double __value) __attribute__ ((__nothrow__ , __leaf__))
  __attribute__ ((__const__));
extern int __iseqsig (double __x, double __y) __attribute__ ((__nothrow__ , __leaf__));
extern int __issignaling (double __value) __attribute__ ((__nothrow__ , __leaf__))
     __attribute__ ((__const__));
 extern double acos (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern double __acos (double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern double asin (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern double __asin (double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern double atan (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern double __atan (double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern double atan2 (double __y, double __x) __attribute__ ((__nothrow__ , __leaf__)); extern double __atan2 (double __y, double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern double cos (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern double __cos (double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern double sin (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern double __sin (double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern double tan (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern double __tan (double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern double cosh (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern double __cosh (double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern double sinh (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern double __sinh (double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern double tanh (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern double __tanh (double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern double acosh (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern double __acosh (double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern double asinh (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern double __asinh (double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern double atanh (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern double __atanh (double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern double exp (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern double __exp (double __x) __attribute__ ((__nothrow__ , __leaf__));
extern double frexp (double __x, int *__exponent) __attribute__ ((__nothrow__ , __leaf__)); extern double __frexp (double __x, int *__exponent) __attribute__ ((__nothrow__ , __leaf__));
extern double ldexp (double __x, int __exponent) __attribute__ ((__nothrow__ , __leaf__)); extern double __ldexp (double __x, int __exponent) __attribute__ ((__nothrow__ , __leaf__));
 extern double log (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern double __log (double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern double log10 (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern double __log10 (double __x) __attribute__ ((__nothrow__ , __leaf__));
extern double modf (double __x, double *__iptr) __attribute__ ((__nothrow__ , __leaf__)); extern double __modf (double __x, double *__iptr) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2)));
 extern double expm1 (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern double __expm1 (double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern double log1p (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern double __log1p (double __x) __attribute__ ((__nothrow__ , __leaf__));
extern double logb (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern double __logb (double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern double exp2 (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern double __exp2 (double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern double log2 (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern double __log2 (double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern double pow (double __x, double __y) __attribute__ ((__nothrow__ , __leaf__)); extern double __pow (double __x, double __y) __attribute__ ((__nothrow__ , __leaf__));
extern double sqrt (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern double __sqrt (double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern double hypot (double __x, double __y) __attribute__ ((__nothrow__ , __leaf__)); extern double __hypot (double __x, double __y) __attribute__ ((__nothrow__ , __leaf__));
 extern double cbrt (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern double __cbrt (double __x) __attribute__ ((__nothrow__ , __leaf__));
extern double ceil (double __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__)); extern double __ceil (double __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern double fabs (double __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__)); extern double __fabs (double __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern double floor (double __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__)); extern double __floor (double __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern double fmod (double __x, double __y) __attribute__ ((__nothrow__ , __leaf__)); extern double __fmod (double __x, double __y) __attribute__ ((__nothrow__ , __leaf__));
extern int isinf (double __value) __attribute__ ((__nothrow__ , __leaf__))
  __attribute__ ((__const__));
extern int finite (double __value) __attribute__ ((__nothrow__ , __leaf__))
  __attribute__ ((__const__));
extern double drem (double __x, double __y) __attribute__ ((__nothrow__ , __leaf__)); extern double __drem (double __x, double __y) __attribute__ ((__nothrow__ , __leaf__));
extern double significand (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern double __significand (double __x) __attribute__ ((__nothrow__ , __leaf__));
extern double copysign (double __x, double __y) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__)); extern double __copysign (double __x, double __y) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern double nan (const char *__tagb) __attribute__ ((__nothrow__ , __leaf__)); extern double __nan (const char *__tagb) __attribute__ ((__nothrow__ , __leaf__));
extern int isnan (double __value) __attribute__ ((__nothrow__ , __leaf__))
  __attribute__ ((__const__));
extern double j0 (double) __attribute__ ((__nothrow__ , __leaf__)); extern double __j0 (double) __attribute__ ((__nothrow__ , __leaf__));
extern double j1 (double) __attribute__ ((__nothrow__ , __leaf__)); extern double __j1 (double) __attribute__ ((__nothrow__ , __leaf__));
extern double jn (int, double) __attribute__ ((__nothrow__ , __leaf__)); extern double __jn (int, double) __attribute__ ((__nothrow__ , __leaf__));
extern double y0 (double) __attribute__ ((__nothrow__ , __leaf__)); extern double __y0 (double) __attribute__ ((__nothrow__ , __leaf__));
extern double y1 (double) __attribute__ ((__nothrow__ , __leaf__)); extern double __y1 (double) __attribute__ ((__nothrow__ , __leaf__));
extern double yn (int, double) __attribute__ ((__nothrow__ , __leaf__)); extern double __yn (int, double) __attribute__ ((__nothrow__ , __leaf__));
 extern double erf (double) __attribute__ ((__nothrow__ , __leaf__)); extern double __erf (double) __attribute__ ((__nothrow__ , __leaf__));
 extern double erfc (double) __attribute__ ((__nothrow__ , __leaf__)); extern double __erfc (double) __attribute__ ((__nothrow__ , __leaf__));
extern double lgamma (double) __attribute__ ((__nothrow__ , __leaf__)); extern double __lgamma (double) __attribute__ ((__nothrow__ , __leaf__));
extern double tgamma (double) __attribute__ ((__nothrow__ , __leaf__)); extern double __tgamma (double) __attribute__ ((__nothrow__ , __leaf__));
extern double gamma (double) __attribute__ ((__nothrow__ , __leaf__)); extern double __gamma (double) __attribute__ ((__nothrow__ , __leaf__));
extern double lgamma_r (double, int *__signgamp) __attribute__ ((__nothrow__ , __leaf__)); extern double __lgamma_r (double, int *__signgamp) __attribute__ ((__nothrow__ , __leaf__));
extern double rint (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern double __rint (double __x) __attribute__ ((__nothrow__ , __leaf__));
extern double nextafter (double __x, double __y) __attribute__ ((__nothrow__ , __leaf__)); extern double __nextafter (double __x, double __y) __attribute__ ((__nothrow__ , __leaf__));
extern double nexttoward (double __x, long double __y) __attribute__ ((__nothrow__ , __leaf__)); extern double __nexttoward (double __x, long double __y) __attribute__ ((__nothrow__ , __leaf__));
extern double remainder (double __x, double __y) __attribute__ ((__nothrow__ , __leaf__)); extern double __remainder (double __x, double __y) __attribute__ ((__nothrow__ , __leaf__));
extern double scalbn (double __x, int __n) __attribute__ ((__nothrow__ , __leaf__)); extern double __scalbn (double __x, int __n) __attribute__ ((__nothrow__ , __leaf__));
extern int ilogb (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern int __ilogb (double __x) __attribute__ ((__nothrow__ , __leaf__));
extern double scalbln (double __x, long int __n) __attribute__ ((__nothrow__ , __leaf__)); extern double __scalbln (double __x, long int __n) __attribute__ ((__nothrow__ , __leaf__));
extern double nearbyint (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern double __nearbyint (double __x) __attribute__ ((__nothrow__ , __leaf__));
extern double round (double __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__)); extern double __round (double __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern double trunc (double __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__)); extern double __trunc (double __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern double remquo (double __x, double __y, int *__quo) __attribute__ ((__nothrow__ , __leaf__)); extern double __remquo (double __x, double __y, int *__quo) __attribute__ ((__nothrow__ , __leaf__));
extern long int lrint (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long int __lrint (double __x) __attribute__ ((__nothrow__ , __leaf__));
__extension__
extern long long int llrint (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long long int __llrint (double __x) __attribute__ ((__nothrow__ , __leaf__));
extern long int lround (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long int __lround (double __x) __attribute__ ((__nothrow__ , __leaf__));
__extension__
extern long long int llround (double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long long int __llround (double __x) __attribute__ ((__nothrow__ , __leaf__));
extern double fdim (double __x, double __y) __attribute__ ((__nothrow__ , __leaf__)); extern double __fdim (double __x, double __y) __attribute__ ((__nothrow__ , __leaf__));
extern double fmax (double __x, double __y) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__)); extern double __fmax (double __x, double __y) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern double fmin (double __x, double __y) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__)); extern double __fmin (double __x, double __y) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern double fma (double __x, double __y, double __z) __attribute__ ((__nothrow__ , __leaf__)); extern double __fma (double __x, double __y, double __z) __attribute__ ((__nothrow__ , __leaf__));
extern double scalb (double __x, double __n) __attribute__ ((__nothrow__ , __leaf__)); extern double __scalb (double __x, double __n) __attribute__ ((__nothrow__ , __leaf__));
extern int __fpclassifyf (float __value) __attribute__ ((__nothrow__ , __leaf__))
     __attribute__ ((__const__));
extern int __signbitf (float __value) __attribute__ ((__nothrow__ , __leaf__))
     __attribute__ ((__const__));
extern int __isinff (float __value) __attribute__ ((__nothrow__ , __leaf__))
  __attribute__ ((__const__));
extern int __finitef (float __value) __attribute__ ((__nothrow__ , __leaf__))
  __attribute__ ((__const__));
extern int __isnanf (float __value) __attribute__ ((__nothrow__ , __leaf__))
  __attribute__ ((__const__));
extern int __iseqsigf (float __x, float __y) __attribute__ ((__nothrow__ , __leaf__));
extern int __issignalingf (float __value) __attribute__ ((__nothrow__ , __leaf__))
     __attribute__ ((__const__));
 extern float acosf (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern float __acosf (float __x) __attribute__ ((__nothrow__ , __leaf__));
 extern float asinf (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern float __asinf (float __x) __attribute__ ((__nothrow__ , __leaf__));
 extern float atanf (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern float __atanf (float __x) __attribute__ ((__nothrow__ , __leaf__));
 extern float atan2f (float __y, float __x) __attribute__ ((__nothrow__ , __leaf__)); extern float __atan2f (float __y, float __x) __attribute__ ((__nothrow__ , __leaf__));
 extern float cosf (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern float __cosf (float __x) __attribute__ ((__nothrow__ , __leaf__));
 extern float sinf (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern float __sinf (float __x) __attribute__ ((__nothrow__ , __leaf__));
 extern float tanf (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern float __tanf (float __x) __attribute__ ((__nothrow__ , __leaf__));
 extern float coshf (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern float __coshf (float __x) __attribute__ ((__nothrow__ , __leaf__));
 extern float sinhf (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern float __sinhf (float __x) __attribute__ ((__nothrow__ , __leaf__));
 extern float tanhf (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern float __tanhf (float __x) __attribute__ ((__nothrow__ , __leaf__));
 extern float acoshf (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern float __acoshf (float __x) __attribute__ ((__nothrow__ , __leaf__));
 extern float asinhf (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern float __asinhf (float __x) __attribute__ ((__nothrow__ , __leaf__));
 extern float atanhf (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern float __atanhf (float __x) __attribute__ ((__nothrow__ , __leaf__));
 extern float expf (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern float __expf (float __x) __attribute__ ((__nothrow__ , __leaf__));
extern float frexpf (float __x, int *__exponent) __attribute__ ((__nothrow__ , __leaf__)); extern float __frexpf (float __x, int *__exponent) __attribute__ ((__nothrow__ , __leaf__));
extern float ldexpf (float __x, int __exponent) __attribute__ ((__nothrow__ , __leaf__)); extern float __ldexpf (float __x, int __exponent) __attribute__ ((__nothrow__ , __leaf__));
 extern float logf (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern float __logf (float __x) __attribute__ ((__nothrow__ , __leaf__));
 extern float log10f (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern float __log10f (float __x) __attribute__ ((__nothrow__ , __leaf__));
extern float modff (float __x, float *__iptr) __attribute__ ((__nothrow__ , __leaf__)); extern float __modff (float __x, float *__iptr) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2)));
 extern float expm1f (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern float __expm1f (float __x) __attribute__ ((__nothrow__ , __leaf__));
 extern float log1pf (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern float __log1pf (float __x) __attribute__ ((__nothrow__ , __leaf__));
extern float logbf (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern float __logbf (float __x) __attribute__ ((__nothrow__ , __leaf__));
 extern float exp2f (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern float __exp2f (float __x) __attribute__ ((__nothrow__ , __leaf__));
 extern float log2f (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern float __log2f (float __x) __attribute__ ((__nothrow__ , __leaf__));
 extern float powf (float __x, float __y) __attribute__ ((__nothrow__ , __leaf__)); extern float __powf (float __x, float __y) __attribute__ ((__nothrow__ , __leaf__));
extern float sqrtf (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern float __sqrtf (float __x) __attribute__ ((__nothrow__ , __leaf__));
 extern float hypotf (float __x, float __y) __attribute__ ((__nothrow__ , __leaf__)); extern float __hypotf (float __x, float __y) __attribute__ ((__nothrow__ , __leaf__));
 extern float cbrtf (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern float __cbrtf (float __x) __attribute__ ((__nothrow__ , __leaf__));
extern float ceilf (float __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__)); extern float __ceilf (float __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern float fabsf (float __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__)); extern float __fabsf (float __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern float floorf (float __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__)); extern float __floorf (float __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern float fmodf (float __x, float __y) __attribute__ ((__nothrow__ , __leaf__)); extern float __fmodf (float __x, float __y) __attribute__ ((__nothrow__ , __leaf__));
extern int isinff (float __value) __attribute__ ((__nothrow__ , __leaf__))
  __attribute__ ((__const__));
extern int finitef (float __value) __attribute__ ((__nothrow__ , __leaf__))
  __attribute__ ((__const__));
extern float dremf (float __x, float __y) __attribute__ ((__nothrow__ , __leaf__)); extern float __dremf (float __x, float __y) __attribute__ ((__nothrow__ , __leaf__));
extern float significandf (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern float __significandf (float __x) __attribute__ ((__nothrow__ , __leaf__));
extern float copysignf (float __x, float __y) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__)); extern float __copysignf (float __x, float __y) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern float nanf (const char *__tagb) __attribute__ ((__nothrow__ , __leaf__)); extern float __nanf (const char *__tagb) __attribute__ ((__nothrow__ , __leaf__));
extern int isnanf (float __value) __attribute__ ((__nothrow__ , __leaf__))
  __attribute__ ((__const__));
extern float j0f (float) __attribute__ ((__nothrow__ , __leaf__)); extern float __j0f (float) __attribute__ ((__nothrow__ , __leaf__));
extern float j1f (float) __attribute__ ((__nothrow__ , __leaf__)); extern float __j1f (float) __attribute__ ((__nothrow__ , __leaf__));
extern float jnf (int, float) __attribute__ ((__nothrow__ , __leaf__)); extern float __jnf (int, float) __attribute__ ((__nothrow__ , __leaf__));
extern float y0f (float) __attribute__ ((__nothrow__ , __leaf__)); extern float __y0f (float) __attribute__ ((__nothrow__ , __leaf__));
extern float y1f (float) __attribute__ ((__nothrow__ , __leaf__)); extern float __y1f (float) __attribute__ ((__nothrow__ , __leaf__));
extern float ynf (int, float) __attribute__ ((__nothrow__ , __leaf__)); extern float __ynf (int, float) __attribute__ ((__nothrow__ , __leaf__));
 extern float erff (float) __attribute__ ((__nothrow__ , __leaf__)); extern float __erff (float) __attribute__ ((__nothrow__ , __leaf__));
 extern float erfcf (float) __attribute__ ((__nothrow__ , __leaf__)); extern float __erfcf (float) __attribute__ ((__nothrow__ , __leaf__));
extern float lgammaf (float) __attribute__ ((__nothrow__ , __leaf__)); extern float __lgammaf (float) __attribute__ ((__nothrow__ , __leaf__));
extern float tgammaf (float) __attribute__ ((__nothrow__ , __leaf__)); extern float __tgammaf (float) __attribute__ ((__nothrow__ , __leaf__));
extern float gammaf (float) __attribute__ ((__nothrow__ , __leaf__)); extern float __gammaf (float) __attribute__ ((__nothrow__ , __leaf__));
extern float lgammaf_r (float, int *__signgamp) __attribute__ ((__nothrow__ , __leaf__)); extern float __lgammaf_r (float, int *__signgamp) __attribute__ ((__nothrow__ , __leaf__));
extern float rintf (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern float __rintf (float __x) __attribute__ ((__nothrow__ , __leaf__));
extern float nextafterf (float __x, float __y) __attribute__ ((__nothrow__ , __leaf__)); extern float __nextafterf (float __x, float __y) __attribute__ ((__nothrow__ , __leaf__));
extern float nexttowardf (float __x, long double __y) __attribute__ ((__nothrow__ , __leaf__)); extern float __nexttowardf (float __x, long double __y) __attribute__ ((__nothrow__ , __leaf__));
extern float remainderf (float __x, float __y) __attribute__ ((__nothrow__ , __leaf__)); extern float __remainderf (float __x, float __y) __attribute__ ((__nothrow__ , __leaf__));
extern float scalbnf (float __x, int __n) __attribute__ ((__nothrow__ , __leaf__)); extern float __scalbnf (float __x, int __n) __attribute__ ((__nothrow__ , __leaf__));
extern int ilogbf (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern int __ilogbf (float __x) __attribute__ ((__nothrow__ , __leaf__));
extern float scalblnf (float __x, long int __n) __attribute__ ((__nothrow__ , __leaf__)); extern float __scalblnf (float __x, long int __n) __attribute__ ((__nothrow__ , __leaf__));
extern float nearbyintf (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern float __nearbyintf (float __x) __attribute__ ((__nothrow__ , __leaf__));
extern float roundf (float __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__)); extern float __roundf (float __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern float truncf (float __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__)); extern float __truncf (float __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern float remquof (float __x, float __y, int *__quo) __attribute__ ((__nothrow__ , __leaf__)); extern float __remquof (float __x, float __y, int *__quo) __attribute__ ((__nothrow__ , __leaf__));
extern long int lrintf (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern long int __lrintf (float __x) __attribute__ ((__nothrow__ , __leaf__));
__extension__
extern long long int llrintf (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern long long int __llrintf (float __x) __attribute__ ((__nothrow__ , __leaf__));
extern long int lroundf (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern long int __lroundf (float __x) __attribute__ ((__nothrow__ , __leaf__));
__extension__
extern long long int llroundf (float __x) __attribute__ ((__nothrow__ , __leaf__)); extern long long int __llroundf (float __x) __attribute__ ((__nothrow__ , __leaf__));
extern float fdimf (float __x, float __y) __attribute__ ((__nothrow__ , __leaf__)); extern float __fdimf (float __x, float __y) __attribute__ ((__nothrow__ , __leaf__));
extern float fmaxf (float __x, float __y) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__)); extern float __fmaxf (float __x, float __y) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern float fminf (float __x, float __y) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__)); extern float __fminf (float __x, float __y) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern float fmaf (float __x, float __y, float __z) __attribute__ ((__nothrow__ , __leaf__)); extern float __fmaf (float __x, float __y, float __z) __attribute__ ((__nothrow__ , __leaf__));
extern float scalbf (float __x, float __n) __attribute__ ((__nothrow__ , __leaf__)); extern float __scalbf (float __x, float __n) __attribute__ ((__nothrow__ , __leaf__));
extern int __fpclassifyl (long double __value) __attribute__ ((__nothrow__ , __leaf__))
     __attribute__ ((__const__));
extern int __signbitl (long double __value) __attribute__ ((__nothrow__ , __leaf__))
     __attribute__ ((__const__));
extern int __isinfl (long double __value) __attribute__ ((__nothrow__ , __leaf__))
  __attribute__ ((__const__));
extern int __finitel (long double __value) __attribute__ ((__nothrow__ , __leaf__))
  __attribute__ ((__const__));
extern int __isnanl (long double __value) __attribute__ ((__nothrow__ , __leaf__))
  __attribute__ ((__const__));
extern int __iseqsigl (long double __x, long double __y) __attribute__ ((__nothrow__ , __leaf__));
extern int __issignalingl (long double __value) __attribute__ ((__nothrow__ , __leaf__))
     __attribute__ ((__const__));
 extern long double acosl (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long double __acosl (long double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern long double asinl (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long double __asinl (long double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern long double atanl (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long double __atanl (long double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern long double atan2l (long double __y, long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long double __atan2l (long double __y, long double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern long double cosl (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long double __cosl (long double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern long double sinl (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long double __sinl (long double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern long double tanl (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long double __tanl (long double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern long double coshl (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long double __coshl (long double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern long double sinhl (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long double __sinhl (long double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern long double tanhl (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long double __tanhl (long double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern long double acoshl (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long double __acoshl (long double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern long double asinhl (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long double __asinhl (long double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern long double atanhl (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long double __atanhl (long double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern long double expl (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long double __expl (long double __x) __attribute__ ((__nothrow__ , __leaf__));
extern long double frexpl (long double __x, int *__exponent) __attribute__ ((__nothrow__ , __leaf__)); extern long double __frexpl (long double __x, int *__exponent) __attribute__ ((__nothrow__ , __leaf__));
extern long double ldexpl (long double __x, int __exponent) __attribute__ ((__nothrow__ , __leaf__)); extern long double __ldexpl (long double __x, int __exponent) __attribute__ ((__nothrow__ , __leaf__));
 extern long double logl (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long double __logl (long double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern long double log10l (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long double __log10l (long double __x) __attribute__ ((__nothrow__ , __leaf__));
extern long double modfl (long double __x, long double *__iptr) __attribute__ ((__nothrow__ , __leaf__)); extern long double __modfl (long double __x, long double *__iptr) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2)));
 extern long double expm1l (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long double __expm1l (long double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern long double log1pl (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long double __log1pl (long double __x) __attribute__ ((__nothrow__ , __leaf__));
extern long double logbl (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long double __logbl (long double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern long double exp2l (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long double __exp2l (long double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern long double log2l (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long double __log2l (long double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern long double powl (long double __x, long double __y) __attribute__ ((__nothrow__ , __leaf__)); extern long double __powl (long double __x, long double __y) __attribute__ ((__nothrow__ , __leaf__));
extern long double sqrtl (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long double __sqrtl (long double __x) __attribute__ ((__nothrow__ , __leaf__));
 extern long double hypotl (long double __x, long double __y) __attribute__ ((__nothrow__ , __leaf__)); extern long double __hypotl (long double __x, long double __y) __attribute__ ((__nothrow__ , __leaf__));
 extern long double cbrtl (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long double __cbrtl (long double __x) __attribute__ ((__nothrow__ , __leaf__));
extern long double ceill (long double __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__)); extern long double __ceill (long double __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern long double fabsl (long double __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__)); extern long double __fabsl (long double __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern long double floorl (long double __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__)); extern long double __floorl (long double __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern long double fmodl (long double __x, long double __y) __attribute__ ((__nothrow__ , __leaf__)); extern long double __fmodl (long double __x, long double __y) __attribute__ ((__nothrow__ , __leaf__));
extern int isinfl (long double __value) __attribute__ ((__nothrow__ , __leaf__))
  __attribute__ ((__const__));
extern int finitel (long double __value) __attribute__ ((__nothrow__ , __leaf__))
  __attribute__ ((__const__));
extern long double dreml (long double __x, long double __y) __attribute__ ((__nothrow__ , __leaf__)); extern long double __dreml (long double __x, long double __y) __attribute__ ((__nothrow__ , __leaf__));
extern long double significandl (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long double __significandl (long double __x) __attribute__ ((__nothrow__ , __leaf__));
extern long double copysignl (long double __x, long double __y) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__)); extern long double __copysignl (long double __x, long double __y) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern long double nanl (const char *__tagb) __attribute__ ((__nothrow__ , __leaf__)); extern long double __nanl (const char *__tagb) __attribute__ ((__nothrow__ , __leaf__));
extern int isnanl (long double __value) __attribute__ ((__nothrow__ , __leaf__))
  __attribute__ ((__const__));
extern long double j0l (long double) __attribute__ ((__nothrow__ , __leaf__)); extern long double __j0l (long double) __attribute__ ((__nothrow__ , __leaf__));
extern long double j1l (long double) __attribute__ ((__nothrow__ , __leaf__)); extern long double __j1l (long double) __attribute__ ((__nothrow__ , __leaf__));
extern long double jnl (int, long double) __attribute__ ((__nothrow__ , __leaf__)); extern long double __jnl (int, long double) __attribute__ ((__nothrow__ , __leaf__));
extern long double y0l (long double) __attribute__ ((__nothrow__ , __leaf__)); extern long double __y0l (long double) __attribute__ ((__nothrow__ , __leaf__));
extern long double y1l (long double) __attribute__ ((__nothrow__ , __leaf__)); extern long double __y1l (long double) __attribute__ ((__nothrow__ , __leaf__));
extern long double ynl (int, long double) __attribute__ ((__nothrow__ , __leaf__)); extern long double __ynl (int, long double) __attribute__ ((__nothrow__ , __leaf__));
 extern long double erfl (long double) __attribute__ ((__nothrow__ , __leaf__)); extern long double __erfl (long double) __attribute__ ((__nothrow__ , __leaf__));
 extern long double erfcl (long double) __attribute__ ((__nothrow__ , __leaf__)); extern long double __erfcl (long double) __attribute__ ((__nothrow__ , __leaf__));
extern long double lgammal (long double) __attribute__ ((__nothrow__ , __leaf__)); extern long double __lgammal (long double) __attribute__ ((__nothrow__ , __leaf__));
extern long double tgammal (long double) __attribute__ ((__nothrow__ , __leaf__)); extern long double __tgammal (long double) __attribute__ ((__nothrow__ , __leaf__));
extern long double gammal (long double) __attribute__ ((__nothrow__ , __leaf__)); extern long double __gammal (long double) __attribute__ ((__nothrow__ , __leaf__));
extern long double lgammal_r (long double, int *__signgamp) __attribute__ ((__nothrow__ , __leaf__)); extern long double __lgammal_r (long double, int *__signgamp) __attribute__ ((__nothrow__ , __leaf__));
extern long double rintl (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long double __rintl (long double __x) __attribute__ ((__nothrow__ , __leaf__));
extern long double nextafterl (long double __x, long double __y) __attribute__ ((__nothrow__ , __leaf__)); extern long double __nextafterl (long double __x, long double __y) __attribute__ ((__nothrow__ , __leaf__));
extern long double nexttowardl (long double __x, long double __y) __attribute__ ((__nothrow__ , __leaf__)); extern long double __nexttowardl (long double __x, long double __y) __attribute__ ((__nothrow__ , __leaf__));
extern long double remainderl (long double __x, long double __y) __attribute__ ((__nothrow__ , __leaf__)); extern long double __remainderl (long double __x, long double __y) __attribute__ ((__nothrow__ , __leaf__));
extern long double scalbnl (long double __x, int __n) __attribute__ ((__nothrow__ , __leaf__)); extern long double __scalbnl (long double __x, int __n) __attribute__ ((__nothrow__ , __leaf__));
extern int ilogbl (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern int __ilogbl (long double __x) __attribute__ ((__nothrow__ , __leaf__));
extern long double scalblnl (long double __x, long int __n) __attribute__ ((__nothrow__ , __leaf__)); extern long double __scalblnl (long double __x, long int __n) __attribute__ ((__nothrow__ , __leaf__));
extern long double nearbyintl (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long double __nearbyintl (long double __x) __attribute__ ((__nothrow__ , __leaf__));
extern long double roundl (long double __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__)); extern long double __roundl (long double __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern long double truncl (long double __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__)); extern long double __truncl (long double __x) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern long double remquol (long double __x, long double __y, int *__quo) __attribute__ ((__nothrow__ , __leaf__)); extern long double __remquol (long double __x, long double __y, int *__quo) __attribute__ ((__nothrow__ , __leaf__));
extern long int lrintl (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long int __lrintl (long double __x) __attribute__ ((__nothrow__ , __leaf__));
__extension__
extern long long int llrintl (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long long int __llrintl (long double __x) __attribute__ ((__nothrow__ , __leaf__));
extern long int lroundl (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long int __lroundl (long double __x) __attribute__ ((__nothrow__ , __leaf__));
__extension__
extern long long int llroundl (long double __x) __attribute__ ((__nothrow__ , __leaf__)); extern long long int __llroundl (long double __x) __attribute__ ((__nothrow__ , __leaf__));
extern long double fdiml (long double __x, long double __y) __attribute__ ((__nothrow__ , __leaf__)); extern long double __fdiml (long double __x, long double __y) __attribute__ ((__nothrow__ , __leaf__));
extern long double fmaxl (long double __x, long double __y) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__)); extern long double __fmaxl (long double __x, long double __y) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern long double fminl (long double __x, long double __y) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__)); extern long double __fminl (long double __x, long double __y) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern long double fmal (long double __x, long double __y, long double __z) __attribute__ ((__nothrow__ , __leaf__)); extern long double __fmal (long double __x, long double __y, long double __z) __attribute__ ((__nothrow__ , __leaf__));
extern long double scalbl (long double __x, long double __n) __attribute__ ((__nothrow__ , __leaf__)); extern long double __scalbl (long double __x, long double __n) __attribute__ ((__nothrow__ , __leaf__));
extern int __fpclassifyf128 (_Float128 __value) __attribute__ ((__nothrow__ , __leaf__))
     __attribute__ ((__const__));
extern int __signbitf128 (_Float128 __value) __attribute__ ((__nothrow__ , __leaf__))
     __attribute__ ((__const__));
extern int __isinff128 (_Float128 __value) __attribute__ ((__nothrow__ , __leaf__))
  __attribute__ ((__const__));
extern int __finitef128 (_Float128 __value) __attribute__ ((__nothrow__ , __leaf__))
  __attribute__ ((__const__));
extern int __isnanf128 (_Float128 __value) __attribute__ ((__nothrow__ , __leaf__))
  __attribute__ ((__const__));
extern int __iseqsigf128 (_Float128 __x, _Float128 __y) __attribute__ ((__nothrow__ , __leaf__));
extern int __issignalingf128 (_Float128 __value) __attribute__ ((__nothrow__ , __leaf__))
     __attribute__ ((__const__));
extern int signgam;
enum
  {
    FP_NAN =
      0,
    FP_INFINITE =
      1,
    FP_ZERO =
      2,
    FP_SUBNORMAL =
      3,
    FP_NORMAL =
      4
  };

typedef __int8_t int8_t;
typedef __int16_t int16_t;
typedef __int32_t int32_t;
typedef __int64_t int64_t;
typedef __uint8_t uint8_t;
typedef __uint16_t uint16_t;
typedef __uint32_t uint32_t;
typedef __uint64_t uint64_t;
typedef __int_least8_t int_least8_t;
typedef __int_least16_t int_least16_t;
typedef __int_least32_t int_least32_t;
typedef __int_least64_t int_least64_t;
typedef __uint_least8_t uint_least8_t;
typedef __uint_least16_t uint_least16_t;
typedef __uint_least32_t uint_least32_t;
typedef __uint_least64_t uint_least64_t;
typedef signed char int_fast8_t;
typedef long int int_fast16_t;
typedef long int int_fast32_t;
typedef long int int_fast64_t;
typedef unsigned char uint_fast8_t;
typedef unsigned long int uint_fast16_t;
typedef unsigned long int uint_fast32_t;
typedef unsigned long int uint_fast64_t;
typedef long int intptr_t;
typedef unsigned long int uintptr_t;
typedef __intmax_t intmax_t;
typedef __uintmax_t uintmax_t;

extern void __assert_fail (const char *__assertion, const char *__file,
      unsigned int __line, const char *__function)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__noreturn__));
extern void __assert_perror_fail (int __errnum, const char *__file,
      unsigned int __line, const char *__function)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__noreturn__));
extern void __assert (const char *__assertion, const char *__file, int __line)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__noreturn__));


typedef __builtin_va_list __gnuc_va_list;
typedef struct
{
  int __count;
  union
  {
    unsigned int __wch;
    char __wchb[4];
  } __value;
} __mbstate_t;
typedef struct _G_fpos_t
{
  __off_t __pos;
  __mbstate_t __state;
} __fpos_t;
typedef struct _G_fpos64_t
{
  __off64_t __pos;
  __mbstate_t __state;
} __fpos64_t;
struct _IO_FILE;
typedef struct _IO_FILE __FILE;
struct _IO_FILE;
typedef struct _IO_FILE FILE;
struct _IO_FILE;
struct _IO_marker;
struct _IO_codecvt;
struct _IO_wide_data;
typedef void _IO_lock_t;
struct _IO_FILE
{
  int _flags;
  char *_IO_read_ptr;
  char *_IO_read_end;
  char *_IO_read_base;
  char *_IO_write_base;
  char *_IO_write_ptr;
  char *_IO_write_end;
  char *_IO_buf_base;
  char *_IO_buf_end;
  char *_IO_save_base;
  char *_IO_backup_base;
  char *_IO_save_end;
  struct _IO_marker *_markers;
  struct _IO_FILE *_chain;
  int _fileno;
  int _flags2;
  __off_t _old_offset;
  unsigned short _cur_column;
  signed char _vtable_offset;
  char _shortbuf[1];
  _IO_lock_t *_lock;
  __off64_t _offset;
  struct _IO_codecvt *_codecvt;
  struct _IO_wide_data *_wide_data;
  struct _IO_FILE *_freeres_list;
  void *_freeres_buf;
  size_t __pad5;
  int _mode;
  char _unused2[15 * sizeof (int) - 4 * sizeof (void *) - sizeof (size_t)];
};
typedef __gnuc_va_list va_list;
typedef __off_t off_t;
typedef __ssize_t ssize_t;
typedef __fpos_t fpos_t;
extern FILE *stdin;
extern FILE *stdout;
extern FILE *stderr;
extern int remove (const char *__filename) __attribute__ ((__nothrow__ , __leaf__));
extern int rename (const char *__old, const char *__new) __attribute__ ((__nothrow__ , __leaf__));
extern int renameat (int __oldfd, const char *__old, int __newfd,
       const char *__new) __attribute__ ((__nothrow__ , __leaf__));
extern int fclose (FILE *__stream);
extern FILE *tmpfile (void)
  __attribute__ ((__malloc__)) __attribute__ ((__malloc__ (fclose, 1))) ;
extern char *tmpnam (char[20]) __attribute__ ((__nothrow__ , __leaf__)) ;
extern char *tmpnam_r (char __s[20]) __attribute__ ((__nothrow__ , __leaf__)) ;
extern char *tempnam (const char *__dir, const char *__pfx)
   __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__malloc__)) __attribute__ ((__malloc__ (__builtin_free, 1)));
extern int fflush (FILE *__stream);
extern int fflush_unlocked (FILE *__stream);
extern FILE *fopen (const char *__restrict __filename,
      const char *__restrict __modes)
  __attribute__ ((__malloc__)) __attribute__ ((__malloc__ (fclose, 1))) ;
extern FILE *freopen (const char *__restrict __filename,
        const char *__restrict __modes,
        FILE *__restrict __stream) ;
extern FILE *fdopen (int __fd, const char *__modes) __attribute__ ((__nothrow__ , __leaf__))
  __attribute__ ((__malloc__)) __attribute__ ((__malloc__ (fclose, 1))) ;
extern FILE *fmemopen (void *__s, size_t __len, const char *__modes)
  __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__malloc__)) __attribute__ ((__malloc__ (fclose, 1))) ;
extern FILE *open_memstream (char **__bufloc, size_t *__sizeloc) __attribute__ ((__nothrow__ , __leaf__))
  __attribute__ ((__malloc__)) __attribute__ ((__malloc__ (fclose, 1))) ;
extern void setbuf (FILE *__restrict __stream, char *__restrict __buf) __attribute__ ((__nothrow__ , __leaf__));
extern int setvbuf (FILE *__restrict __stream, char *__restrict __buf,
      int __modes, size_t __n) __attribute__ ((__nothrow__ , __leaf__));
extern void setbuffer (FILE *__restrict __stream, char *__restrict __buf,
         size_t __size) __attribute__ ((__nothrow__ , __leaf__));
extern void setlinebuf (FILE *__stream) __attribute__ ((__nothrow__ , __leaf__));
extern int fprintf (FILE *__restrict __stream,
      const char *__restrict __format, ...);
extern int printf (const char *__restrict __format, ...);
extern int sprintf (char *__restrict __s,
      const char *__restrict __format, ...) __attribute__ ((__nothrow__));
extern int vfprintf (FILE *__restrict __s, const char *__restrict __format,
       __gnuc_va_list __arg);
extern int vprintf (const char *__restrict __format, __gnuc_va_list __arg);
extern int vsprintf (char *__restrict __s, const char *__restrict __format,
       __gnuc_va_list __arg) __attribute__ ((__nothrow__));
extern int snprintf (char *__restrict __s, size_t __maxlen,
       const char *__restrict __format, ...)
     __attribute__ ((__nothrow__)) __attribute__ ((__format__ (__printf__, 3, 4)));
extern int vsnprintf (char *__restrict __s, size_t __maxlen,
        const char *__restrict __format, __gnuc_va_list __arg)
     __attribute__ ((__nothrow__)) __attribute__ ((__format__ (__printf__, 3, 0)));
extern int vdprintf (int __fd, const char *__restrict __fmt,
       __gnuc_va_list __arg)
     __attribute__ ((__format__ (__printf__, 2, 0)));
extern int dprintf (int __fd, const char *__restrict __fmt, ...)
     __attribute__ ((__format__ (__printf__, 2, 3)));
extern int fscanf (FILE *__restrict __stream,
     const char *__restrict __format, ...) ;
extern int scanf (const char *__restrict __format, ...) ;
extern int sscanf (const char *__restrict __s,
     const char *__restrict __format, ...) __attribute__ ((__nothrow__ , __leaf__));
extern int fscanf (FILE *__restrict __stream, const char *__restrict __format, ...) __asm__ ("" "__isoc99_fscanf") ;
extern int scanf (const char *__restrict __format, ...) __asm__ ("" "__isoc99_scanf") ;
extern int sscanf (const char *__restrict __s, const char *__restrict __format, ...) __asm__ ("" "__isoc99_sscanf") __attribute__ ((__nothrow__ , __leaf__));
extern int vfscanf (FILE *__restrict __s, const char *__restrict __format,
      __gnuc_va_list __arg)
     __attribute__ ((__format__ (__scanf__, 2, 0))) ;
extern int vscanf (const char *__restrict __format, __gnuc_va_list __arg)
     __attribute__ ((__format__ (__scanf__, 1, 0))) ;
extern int vsscanf (const char *__restrict __s,
      const char *__restrict __format, __gnuc_va_list __arg)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__format__ (__scanf__, 2, 0)));
extern int vfscanf (FILE *__restrict __s, const char *__restrict __format, __gnuc_va_list __arg) __asm__ ("" "__isoc99_vfscanf")
     __attribute__ ((__format__ (__scanf__, 2, 0))) ;
extern int vscanf (const char *__restrict __format, __gnuc_va_list __arg) __asm__ ("" "__isoc99_vscanf")
     __attribute__ ((__format__ (__scanf__, 1, 0))) ;
extern int vsscanf (const char *__restrict __s, const char *__restrict __format, __gnuc_va_list __arg) __asm__ ("" "__isoc99_vsscanf") __attribute__ ((__nothrow__ , __leaf__))
     __attribute__ ((__format__ (__scanf__, 2, 0)));
extern int fgetc (FILE *__stream);
extern int getc (FILE *__stream);
extern int getchar (void);
extern int getc_unlocked (FILE *__stream);
extern int getchar_unlocked (void);
extern int fgetc_unlocked (FILE *__stream);
extern int fputc (int __c, FILE *__stream);
extern int putc (int __c, FILE *__stream);
extern int putchar (int __c);
extern int fputc_unlocked (int __c, FILE *__stream);
extern int putc_unlocked (int __c, FILE *__stream);
extern int putchar_unlocked (int __c);
extern int getw (FILE *__stream);
extern int putw (int __w, FILE *__stream);
extern char *fgets (char *__restrict __s, int __n, FILE *__restrict __stream)
     __attribute__ ((__access__ (__write_only__, 1, 2)));
extern __ssize_t __getdelim (char **__restrict __lineptr,
                             size_t *__restrict __n, int __delimiter,
                             FILE *__restrict __stream) ;
extern __ssize_t getdelim (char **__restrict __lineptr,
                           size_t *__restrict __n, int __delimiter,
                           FILE *__restrict __stream) ;
extern __ssize_t getline (char **__restrict __lineptr,
                          size_t *__restrict __n,
                          FILE *__restrict __stream) ;
extern int fputs (const char *__restrict __s, FILE *__restrict __stream);
extern int puts (const char *__s);
extern int ungetc (int __c, FILE *__stream);
extern size_t fread (void *__restrict __ptr, size_t __size,
       size_t __n, FILE *__restrict __stream) ;
extern size_t fwrite (const void *__restrict __ptr, size_t __size,
        size_t __n, FILE *__restrict __s);
extern size_t fread_unlocked (void *__restrict __ptr, size_t __size,
         size_t __n, FILE *__restrict __stream) ;
extern size_t fwrite_unlocked (const void *__restrict __ptr, size_t __size,
          size_t __n, FILE *__restrict __stream);
extern int fseek (FILE *__stream, long int __off, int __whence);
extern long int ftell (FILE *__stream) ;
extern void rewind (FILE *__stream);
extern int fseeko (FILE *__stream, __off_t __off, int __whence);
extern __off_t ftello (FILE *__stream) ;
extern int fgetpos (FILE *__restrict __stream, fpos_t *__restrict __pos);
extern int fsetpos (FILE *__stream, const fpos_t *__pos);
extern void clearerr (FILE *__stream) __attribute__ ((__nothrow__ , __leaf__));
extern int feof (FILE *__stream) __attribute__ ((__nothrow__ , __leaf__)) ;
extern int ferror (FILE *__stream) __attribute__ ((__nothrow__ , __leaf__)) ;
extern void clearerr_unlocked (FILE *__stream) __attribute__ ((__nothrow__ , __leaf__));
extern int feof_unlocked (FILE *__stream) __attribute__ ((__nothrow__ , __leaf__)) ;
extern int ferror_unlocked (FILE *__stream) __attribute__ ((__nothrow__ , __leaf__)) ;
extern void perror (const char *__s);
extern int fileno (FILE *__stream) __attribute__ ((__nothrow__ , __leaf__)) ;
extern int fileno_unlocked (FILE *__stream) __attribute__ ((__nothrow__ , __leaf__)) ;
extern int pclose (FILE *__stream);
extern FILE *popen (const char *__command, const char *__modes)
  __attribute__ ((__malloc__)) __attribute__ ((__malloc__ (pclose, 1))) ;
extern char *ctermid (char *__s) __attribute__ ((__nothrow__ , __leaf__))
  __attribute__ ((__access__ (__write_only__, 1)));
extern void flockfile (FILE *__stream) __attribute__ ((__nothrow__ , __leaf__));
extern int ftrylockfile (FILE *__stream) __attribute__ ((__nothrow__ , __leaf__)) ;
extern void funlockfile (FILE *__stream) __attribute__ ((__nothrow__ , __leaf__));
extern int __uflow (FILE *);
extern int __overflow (FILE *, int);

static void
platform_main_begin(void)
{
}
static void
platform_main_end(uint32_t crc, int flag)
{
 printf ("checksum = %X\n", crc);
}
static int8_t
(safe_unary_minus_func_int8_t_s)(int8_t si )
{
 
  return
    -si;
}
static int8_t
(safe_add_func_int8_t_s_s)(int8_t si1, int8_t si2 )
{
 
  return
    (si1 + si2);
}
static int8_t
(safe_sub_func_int8_t_s_s)(int8_t si1, int8_t si2 )
{
 
  return
    (si1 - si2);
}
static int8_t
(safe_mul_func_int8_t_s_s)(int8_t si1, int8_t si2 )
{
 
  return
    si1 * si2;
}
static int8_t
(safe_mod_func_int8_t_s_s)(int8_t si1, int8_t si2 )
{
 
  return
    ((si2 == 0) || ((si1 == (-128)) && (si2 == (-1)))) ?
    ((si1)) :
    (si1 % si2);
}
static int8_t
(safe_div_func_int8_t_s_s)(int8_t si1, int8_t si2 )
{
 
  return
    ((si2 == 0) || ((si1 == (-128)) && (si2 == (-1)))) ?
    ((si1)) :
    (si1 / si2);
}
static int8_t
(safe_lshift_func_int8_t_s_s)(int8_t left, int right )
{
 
  return
    ((left < 0) || (((int)right) < 0) || (((int)right) >= 32) || (left > ((127) >> ((int)right)))) ?
    ((left)) :
    (left << ((int)right));
}
static int8_t
(safe_lshift_func_int8_t_s_u)(int8_t left, unsigned int right )
{
 
  return
    ((left < 0) || (((unsigned int)right) >= 32) || (left > ((127) >> ((unsigned int)right)))) ?
    ((left)) :
    (left << ((unsigned int)right));
}
static int8_t
(safe_rshift_func_int8_t_s_s)(int8_t left, int right )
{
 
  return
    ((left < 0) || (((int)right) < 0) || (((int)right) >= 32))?
    ((left)) :
    (left >> ((int)right));
}
static int8_t
(safe_rshift_func_int8_t_s_u)(int8_t left, unsigned int right )
{
 
  return
    ((left < 0) || (((unsigned int)right) >= 32)) ?
    ((left)) :
    (left >> ((unsigned int)right));
}
static int16_t
(safe_unary_minus_func_int16_t_s)(int16_t si )
{
 
  return
    -si;
}
static int16_t
(safe_add_func_int16_t_s_s)(int16_t si1, int16_t si2 )
{
 
  return
    (si1 + si2);
}
static int16_t
(safe_sub_func_int16_t_s_s)(int16_t si1, int16_t si2 )
{
 
  return
    (si1 - si2);
}
static int16_t
(safe_mul_func_int16_t_s_s)(int16_t si1, int16_t si2 )
{
 
  return
    si1 * si2;
}
static int16_t
(safe_mod_func_int16_t_s_s)(int16_t si1, int16_t si2 )
{
 
  return
    ((si2 == 0) || ((si1 == (-32767-1)) && (si2 == (-1)))) ?
    ((si1)) :
    (si1 % si2);
}
static int16_t
(safe_div_func_int16_t_s_s)(int16_t si1, int16_t si2 )
{
 
  return
    ((si2 == 0) || ((si1 == (-32767-1)) && (si2 == (-1)))) ?
    ((si1)) :
    (si1 / si2);
}
static int16_t
(safe_lshift_func_int16_t_s_s)(int16_t left, int right )
{
 
  return
    ((left < 0) || (((int)right) < 0) || (((int)right) >= 32) || (left > ((32767) >> ((int)right)))) ?
    ((left)) :
    (left << ((int)right));
}
static int16_t
(safe_lshift_func_int16_t_s_u)(int16_t left, unsigned int right )
{
 
  return
    ((left < 0) || (((unsigned int)right) >= 32) || (left > ((32767) >> ((unsigned int)right)))) ?
    ((left)) :
    (left << ((unsigned int)right));
}
static int16_t
(safe_rshift_func_int16_t_s_s)(int16_t left, int right )
{
 
  return
    ((left < 0) || (((int)right) < 0) || (((int)right) >= 32))?
    ((left)) :
    (left >> ((int)right));
}
static int16_t
(safe_rshift_func_int16_t_s_u)(int16_t left, unsigned int right )
{
 
  return
    ((left < 0) || (((unsigned int)right) >= 32)) ?
    ((left)) :
    (left >> ((unsigned int)right));
}
static int32_t
(safe_unary_minus_func_int32_t_s)(int32_t si )
{
 
  return
    (si==(-2147483647-1)) ?
    ((si)) :
    -si;
}
static int32_t
(safe_add_func_int32_t_s_s)(int32_t si1, int32_t si2 )
{
 
  return
    (((si1>0) && (si2>0) && (si1 > ((2147483647)-si2))) || ((si1<0) && (si2<0) && (si1 < ((-2147483647-1)-si2)))) ?
    ((si1)) :
    (si1 + si2);
}
static int32_t
(safe_sub_func_int32_t_s_s)(int32_t si1, int32_t si2 )
{
 
  return
    (((si1^si2) & (((si1 ^ ((si1^si2) & (~(2147483647))))-si2)^si2)) < 0) ?
    ((si1)) :
    (si1 - si2);
}
static int32_t
(safe_mul_func_int32_t_s_s)(int32_t si1, int32_t si2 )
{
 
  return
    (((si1 > 0) && (si2 > 0) && (si1 > ((2147483647) / si2))) || ((si1 > 0) && (si2 <= 0) && (si2 < ((-2147483647-1) / si1))) || ((si1 <= 0) && (si2 > 0) && (si1 < ((-2147483647-1) / si2))) || ((si1 <= 0) && (si2 <= 0) && (si1 != 0) && (si2 < ((2147483647) / si1)))) ?
    ((si1)) :
    si1 * si2;
}
static int32_t
(safe_mod_func_int32_t_s_s)(int32_t si1, int32_t si2 )
{
 
  return
    ((si2 == 0) || ((si1 == (-2147483647-1)) && (si2 == (-1)))) ?
    ((si1)) :
    (si1 % si2);
}
static int32_t
(safe_div_func_int32_t_s_s)(int32_t si1, int32_t si2 )
{
 
  return
    ((si2 == 0) || ((si1 == (-2147483647-1)) && (si2 == (-1)))) ?
    ((si1)) :
    (si1 / si2);
}
static int32_t
(safe_lshift_func_int32_t_s_s)(int32_t left, int right )
{
 
  return
    ((left < 0) || (((int)right) < 0) || (((int)right) >= 32) || (left > ((2147483647) >> ((int)right)))) ?
    ((left)) :
    (left << ((int)right));
}
static int32_t
(safe_lshift_func_int32_t_s_u)(int32_t left, unsigned int right )
{
 
  return
    ((left < 0) || (((unsigned int)right) >= 32) || (left > ((2147483647) >> ((unsigned int)right)))) ?
    ((left)) :
    (left << ((unsigned int)right));
}
static int32_t
(safe_rshift_func_int32_t_s_s)(int32_t left, int right )
{
 
  return
    ((left < 0) || (((int)right) < 0) || (((int)right) >= 32))?
    ((left)) :
    (left >> ((int)right));
}
static int32_t
(safe_rshift_func_int32_t_s_u)(int32_t left, unsigned int right )
{
 
  return
    ((left < 0) || (((unsigned int)right) >= 32)) ?
    ((left)) :
    (left >> ((unsigned int)right));
}
static uint8_t
(safe_unary_minus_func_uint8_t_u)(uint8_t ui )
{
 
  return -ui;
}
static uint8_t
(safe_add_func_uint8_t_u_u)(uint8_t ui1, uint8_t ui2 )
{
 
  return ui1 + ui2;
}
static uint8_t
(safe_sub_func_uint8_t_u_u)(uint8_t ui1, uint8_t ui2 )
{
 
  return ui1 - ui2;
}
static uint8_t
(safe_mul_func_uint8_t_u_u)(uint8_t ui1, uint8_t ui2 )
{
 
  return ((unsigned int)ui1) * ((unsigned int)ui2);
}
static uint8_t
(safe_mod_func_uint8_t_u_u)(uint8_t ui1, uint8_t ui2 )
{
 
  return
    (ui2 == 0) ?
    ((ui1)) :
    (ui1 % ui2);
}
static uint8_t
(safe_div_func_uint8_t_u_u)(uint8_t ui1, uint8_t ui2 )
{
 
  return
    (ui2 == 0) ?
    ((ui1)) :
    (ui1 / ui2);
}
static uint8_t
(safe_lshift_func_uint8_t_u_s)(uint8_t left, int right )
{
 
  return
    ((((int)right) < 0) || (((int)right) >= 32) || (left > ((255) >> ((int)right)))) ?
    ((left)) :
    (left << ((int)right));
}
static uint8_t
(safe_lshift_func_uint8_t_u_u)(uint8_t left, unsigned int right )
{
 
  return
    ((((unsigned int)right) >= 32) || (left > ((255) >> ((unsigned int)right)))) ?
    ((left)) :
    (left << ((unsigned int)right));
}
static uint8_t
(safe_rshift_func_uint8_t_u_s)(uint8_t left, int right )
{
 
  return
    ((((int)right) < 0) || (((int)right) >= 32)) ?
    ((left)) :
    (left >> ((int)right));
}
static uint8_t
(safe_rshift_func_uint8_t_u_u)(uint8_t left, unsigned int right )
{
 
  return
    (((unsigned int)right) >= 32) ?
    ((left)) :
    (left >> ((unsigned int)right));
}
static uint16_t
(safe_unary_minus_func_uint16_t_u)(uint16_t ui )
{
 
  return -ui;
}
static uint16_t
(safe_add_func_uint16_t_u_u)(uint16_t ui1, uint16_t ui2 )
{
 
  return ui1 + ui2;
}
static uint16_t
(safe_sub_func_uint16_t_u_u)(uint16_t ui1, uint16_t ui2 )
{
 
  return ui1 - ui2;
}
static uint16_t
(safe_mul_func_uint16_t_u_u)(uint16_t ui1, uint16_t ui2 )
{
 
  return ((unsigned int)ui1) * ((unsigned int)ui2);
}
static uint16_t
(safe_mod_func_uint16_t_u_u)(uint16_t ui1, uint16_t ui2 )
{
 
  return
    (ui2 == 0) ?
    ((ui1)) :
    (ui1 % ui2);
}
static uint16_t
(safe_div_func_uint16_t_u_u)(uint16_t ui1, uint16_t ui2 )
{
 
  return
    (ui2 == 0) ?
    ((ui1)) :
    (ui1 / ui2);
}
static uint16_t
(safe_lshift_func_uint16_t_u_s)(uint16_t left, int right )
{
 
  return
    ((((int)right) < 0) || (((int)right) >= 32) || (left > ((65535) >> ((int)right)))) ?
    ((left)) :
    (left << ((int)right));
}
static uint16_t
(safe_lshift_func_uint16_t_u_u)(uint16_t left, unsigned int right )
{
 
  return
    ((((unsigned int)right) >= 32) || (left > ((65535) >> ((unsigned int)right)))) ?
    ((left)) :
    (left << ((unsigned int)right));
}
static uint16_t
(safe_rshift_func_uint16_t_u_s)(uint16_t left, int right )
{
 
  return
    ((((int)right) < 0) || (((int)right) >= 32)) ?
    ((left)) :
    (left >> ((int)right));
}
static uint16_t
(safe_rshift_func_uint16_t_u_u)(uint16_t left, unsigned int right )
{
 
  return
    (((unsigned int)right) >= 32) ?
    ((left)) :
    (left >> ((unsigned int)right));
}
static uint32_t
(safe_unary_minus_func_uint32_t_u)(uint32_t ui )
{
 
  return -ui;
}
static uint32_t
(safe_add_func_uint32_t_u_u)(uint32_t ui1, uint32_t ui2 )
{
 
  return ui1 + ui2;
}
static uint32_t
(safe_sub_func_uint32_t_u_u)(uint32_t ui1, uint32_t ui2 )
{
 
  return ui1 - ui2;
}
static uint32_t
(safe_mul_func_uint32_t_u_u)(uint32_t ui1, uint32_t ui2 )
{
 
  return ((unsigned int)ui1) * ((unsigned int)ui2);
}
static uint32_t
(safe_mod_func_uint32_t_u_u)(uint32_t ui1, uint32_t ui2 )
{
 
  return
    (ui2 == 0) ?
    ((ui1)) :
    (ui1 % ui2);
}
static uint32_t
(safe_div_func_uint32_t_u_u)(uint32_t ui1, uint32_t ui2 )
{
 
  return
    (ui2 == 0) ?
    ((ui1)) :
    (ui1 / ui2);
}
static uint32_t
(safe_lshift_func_uint32_t_u_s)(uint32_t left, int right )
{
 
  return
    ((((int)right) < 0) || (((int)right) >= 32) || (left > ((4294967295U) >> ((int)right)))) ?
    ((left)) :
    (left << ((int)right));
}
static uint32_t
(safe_lshift_func_uint32_t_u_u)(uint32_t left, unsigned int right )
{
 
  return
    ((((unsigned int)right) >= 32) || (left > ((4294967295U) >> ((unsigned int)right)))) ?
    ((left)) :
    (left << ((unsigned int)right));
}
static uint32_t
(safe_rshift_func_uint32_t_u_s)(uint32_t left, int right )
{
 
  return
    ((((int)right) < 0) || (((int)right) >= 32)) ?
    ((left)) :
    (left >> ((int)right));
}
static uint32_t
(safe_rshift_func_uint32_t_u_u)(uint32_t left, unsigned int right )
{
 
  return
    (((unsigned int)right) >= 32) ?
    ((left)) :
    (left >> ((unsigned int)right));
}
static float
(safe_add_func_float_f_f)(float sf1, float sf2 )
{
 
  return
    (fabsf((0.5f * sf1) + (0.5f * sf2)) > (0.5f * 3.40282346638528859811704183484516925e+38F)) ?
    (sf1) :
    (sf1 + sf2);
}
static float
(safe_sub_func_float_f_f)(float sf1, float sf2 )
{
 
  return
    (fabsf((0.5f * sf1) - (0.5f * sf2)) > (0.5f * 3.40282346638528859811704183484516925e+38F)) ?
    (sf1) :
    (sf1 - sf2);
}
static float
(safe_mul_func_float_f_f)(float sf1, float sf2 )
{
 
  return
    (fabsf((0x1.0p-100f * sf1) * (0x1.0p-28f * sf2)) > (0x1.0p-100f * (0x1.0p-28f * 3.40282346638528859811704183484516925e+38F))) ?
    (sf1) :
    (sf1 * sf2);
}
static float
(safe_div_func_float_f_f)(float sf1, float sf2 )
{
 
  return
    ((fabsf(sf2) < 1.0f) && (((sf2 == 0.0f) || (fabsf((0x1.0p-49f * sf1) / (0x1.0p100f * sf2))) > (0x1.0p-100f * (0x1.0p-49f * 3.40282346638528859811704183484516925e+38F))))) ?
    (sf1) :
    (sf1 / sf2);
}
static double
(safe_add_func_double_f_f)(double sf1, double sf2 )
{
 
  return
    (fabs((0.5 * sf1) + (0.5 * sf2)) > (0.5 * ((double)1.79769313486231570814527423731704357e+308L))) ?
    (sf1) :
    (sf1 + sf2);
}
static double
(safe_sub_func_double_f_f)(double sf1, double sf2 )
{
 
  return
    (fabs((0.5 * sf1) - (0.5 * sf2)) > (0.5 * ((double)1.79769313486231570814527423731704357e+308L))) ?
    (sf1) :
    (sf1 - sf2);
}
static double
(safe_mul_func_double_f_f)(double sf1, double sf2 )
{
 
  return
    (fabs((0x1.0p-100 * sf1) * (0x1.0p-924 * sf2)) > (0x1.0p-100 * (0x1.0p-924 * ((double)1.79769313486231570814527423731704357e+308L)))) ?
    (sf1) :
    (sf1 * sf2);
}
static double
(safe_div_func_double_f_f)(double sf1, double sf2 )
{
 
  return
    ((fabs(sf2) < 1.0) && (((sf2 == 0.0) || (fabs((0x1.0p-974 * sf1) / (0x1.0p100 * sf2))) > (0x1.0p-100 * (0x1.0p-974 * ((double)1.79769313486231570814527423731704357e+308L)))))) ?
    (sf1) :
    (sf1 / sf2);
}
static int32_t
(safe_convert_func_float_to_int32_t)(float sf1 )
{
 
  return
    ((sf1 <= (-2147483647-1)) || (sf1 >= (2147483647))) ?
    ((2147483647)) :
    ((int32_t)(sf1));
}
static uint32_t crc32_tab[256];
static uint32_t crc32_context = 0xFFFFFFFFUL;
static void
crc32_gentab (void)
{
 uint32_t crc;
 const uint32_t poly = 0xEDB88320UL;
 int i, j;
 for (i = 0; i < 256; i++) {
  crc = i;
  for (j = 8; j > 0; j--) {
   if (crc & 1) {
    crc = (crc >> 1) ^ poly;
   } else {
    crc >>= 1;
   }
  }
  crc32_tab[i] = crc;
 }
}
static void
crc32_byte (uint8_t b) {
 crc32_context =
  ((crc32_context >> 8) & 0x00FFFFFF) ^
  crc32_tab[(crc32_context ^ b) & 0xFF];
}
static void
crc32_8bytes (uint32_t val)
{
 crc32_byte ((val>>0) & 0xff);
 crc32_byte ((val>>8) & 0xff);
 crc32_byte ((val>>16) & 0xff);
 crc32_byte ((val>>24) & 0xff);
}
static void
transparent_crc (uint32_t val, char* vname, int flag)
{
 crc32_8bytes(val);
 if (flag) {
    printf("...checksum after hashing %s : %X\n", vname, crc32_context ^ 0xFFFFFFFFU);
 }
}
static void
transparent_crc_bytes (char *ptr, int nbytes, char* vname, int flag)
{
    int i;
    for (i=0; i<nbytes; i++) {
        crc32_byte(ptr[i]);
    }
 if (flag) {
    printf("...checksum after hashing %s : %lX\n", vname, crc32_context ^ 0xFFFFFFFFUL);
 }
}
static long __undefined;
static int32_t g_2 = (-2);
static uint32_t g_3 = 1U;
static int32_t g_33 = 0xDBC9B780;
static uint16_t g_34 = 3U;
static uint32_t g_49 = 4294967290U;
static uint32_t g_54 = 0x5024D8F3;
static int32_t g_83 = 0x9AABF663;
static int8_t g_84 = 0x76;
static uint16_t g_85 = 0x032C;
static int16_t g_86 = (-3);
static uint8_t g_123 = 255U;
static int32_t g_126 = 0x3116D361;
static uint16_t g_170 = 0U;
static int16_t g_171 = 1;
static uint32_t g_172 = 0x6AD03787;
static uint8_t g_214 = 0x98;
static int16_t g_215 = 0x61C0;
static uint16_t g_306 = 0x898C;
static int32_t g_360 = 1;
static int32_t g_522 = 0x56A95073;
static int8_t g_543 = 0;
static uint16_t g_545 = 1U;
static uint8_t g_631 = 0xC8;
static uint32_t func_1(void);
static uint32_t func_4(int32_t p_5, uint16_t p_6, int32_t p_7, int32_t p_8, uint32_t p_9);
static int32_t func_10(uint32_t p_11, int32_t p_12);
static uint16_t func_16(uint32_t p_17, int32_t p_18, int32_t p_19, uint32_t p_20, int8_t p_21);
static uint16_t func_24(uint16_t p_25, uint8_t p_26, uint32_t p_27, int32_t p_28, uint8_t p_29);
static uint8_t func_35(uint16_t p_36, uint32_t p_37, uint32_t p_38, uint32_t p_39);
static uint16_t func_40(int32_t p_41, uint8_t p_42);
static int16_t func_51(int8_t p_52);
static int8_t func_56(uint16_t p_57, int8_t p_58, uint8_t p_59, int8_t p_60);
static uint16_t func_63(int8_t p_64, int8_t p_65);
static uint32_t func_1(void)
{
    uint32_t l_32 = 0xAAB39E22;
    int32_t l_361 = 1;
    int16_t l_362 = 0x0DB0;
    int32_t l_544 = 0x8AC595C2;
    int32_t l_546 = 0x7654F77B;
    uint16_t l_594 = 0x3E47;
    int32_t l_628 = 0x9E081993;
    int16_t l_661 = (-9);
    uint8_t l_697 = 0x12;
    int32_t l_713 = (-8);
    uint16_t l_741 = 2U;
    uint32_t l_743 = 0x48CD43B9;
    if (((g_3 = g_2) <=
         (((func_4(
                func_10(
                    (l_546 =
                         ((-1) &&
                          (g_545 =
                               (l_544 = (~(
                                    g_543 = (safe_lshift_func_uint16_t_u_s(
                                        func_16(
                                            (((((safe_lshift_func_int8_t_s_u(
                                                    (func_24(
                                                         (safe_mod_func_int16_t_s_s(
                                                             0xDEF9,
                                                             (g_34 =
                                                                  (l_32 &&
                                                                   (g_33 =
                                                                        g_2))))),
                                                         func_35(
                                                             (l_361 =
                                                                  ((g_360 =
                                                                        (((((7 ==
                                                                             func_40(
                                                                                 (l_32 !=
                                                                                  g_2),
                                                                                 (safe_add_func_int8_t_s_s(
                                                                                     (safe_sub_func_int32_t_s_s(
                                                                                         ((safe_mod_func_uint16_t_u_u(
                                                                                              g_2,
                                                                                              l_32)) <
                                                                                          g_2),
                                                                                         l_32)),
                                                                                     (-1))))) <
                                                                            g_2) !=
                                                                           g_2) <
                                                                          4294967294U) <
                                                                         g_2)) &
                                                                   (-1))),
                                                             g_2, l_362, l_32),
                                                         l_362, g_2, l_362) ^
                                                     0xCC8B),
                                                    g_2)) > g_2) == 1U) >
                                              g_2) ||
                                             g_522),
                                            l_362, g_2, l_362, g_2),
                                        g_2)))))))),
                    g_2),
                g_2, l_362, l_362, g_2) ||
            l_546) &&
           g_2) ^
          l_362))) {
      DCEMarker0_();
      int16_t l_602 = 0xA366;
      for (g_33 = 0; (g_33 == (-25));
           g_33 = safe_sub_func_int16_t_s_s(g_33, 9)) {
        DCEMarker4_();
        uint32_t l_591 = 0x90819D40;
        l_546 = ((~((safe_mod_func_int8_t_s_s(
                        0x4C,
                        ((l_591 >= ((((l_594 = 0x6A) != 0xD8) < g_522) ||
                                    (!(9U || (l_361 = l_544))))) |
                         ((((safe_mod_func_int16_t_s_s(
                                (safe_rshift_func_int16_t_s_u(
                                    (safe_mod_func_uint16_t_u_u(g_170, l_544)),
                                    11)),
                                l_32)) ||
                            l_602) >= 0x1168) <= l_591)))) > 1)) &&
                 g_34);
      }
    } else {
      DCEMarker1_();
      int8_t l_621 = 0x83;
      int32_t l_632 = (-1);
      g_360 =
          ((safe_mod_func_int16_t_s_s(
               0x2AA5,
               (safe_mod_func_uint16_t_u_u(
                   (safe_mod_func_uint32_t_u_u(
                       (safe_mod_func_uint32_t_u_u(
                           (safe_lshift_func_int16_t_s_s(
                               ((l_632 = (safe_lshift_func_int8_t_s_u(
                                     (l_544 &&
                                      (((safe_sub_func_uint8_t_u_u(
                                            (g_631 =
                                                 ((((safe_sub_func_int8_t_s_s(
                                                        (safe_add_func_int8_t_s_s(
                                                            l_621,
                                                            (safe_add_func_uint16_t_u_u(
                                                                (((l_621 >=
                                                                   ((safe_add_func_int8_t_s_s(
                                                                        g_54,
                                                                        g_34)) >=
                                                                    ((safe_mod_func_uint16_t_u_u(
                                                                         ((g_545 >
                                                                           (g_214 =
                                                                                (l_628 =
                                                                                     253U))) <
                                                                          (safe_rshift_func_int8_t_s_s(
                                                                              (((g_123 =
                                                                                     g_34) &&
                                                                                l_32) <
                                                                               l_32),
                                                                              6))),
                                                                         g_34)) <
                                                                     l_362))) &
                                                                  g_85) <
                                                                 l_594),
                                                                l_621)))),
                                                        g_522)) != l_362) ||
                                                   0xE4E5) ^
                                                  g_49)),
                                            g_126)) |
                                        0xAA8D8FB9) != l_594)),
                                     l_621))) <= g_2),
                               l_544)),
                           4294967295U)),
                       l_546)),
                   l_621)))) != g_83);
      for (g_84 = 0; (g_84 <= 0); g_84++) {
        DCEMarker5_();
        g_522 = (safe_mod_func_int32_t_s_s((+g_123), 0xAD3105DC));
      }
      g_522 = (safe_sub_func_int8_t_s_s(
          ((safe_lshift_func_int8_t_s_s(0, 1)) !=
           (safe_add_func_int32_t_s_s(
               g_126,
               ((g_86 > (g_2 >= l_621)) !=
                (safe_lshift_func_uint8_t_u_s(
                    (((((((safe_lshift_func_uint16_t_u_u(
                              ((+(safe_mod_func_int32_t_s_s(
                                   (l_621 <
                                    (g_543 =
                                         (((l_594 >
                                            (l_621 |
                                             (l_632 =
                                                  (((safe_sub_func_int16_t_s_s(
                                                        (g_360 & g_84),
                                                        g_126)) ||
                                                    g_360) < 0xE6)))) |
                                           g_171) ||
                                          l_621))),
                                   l_621))) &
                               1),
                              6)) == l_544) &&
                         l_621) |
                        0x5C) ^
                       0x3E5292C6) ||
                      g_214) &
                     (-4)),
                    l_621)))))),
          0x4E));
    }
    for (l_628 = 0; (l_628 > 18); l_628++) {
      DCEMarker2_();
      uint16_t l_660 = 0x1C85;
      int32_t l_677 = 0x4590FB8F;
      int16_t l_689 = 0x5AD9;
      l_361 =
          ((safe_rshift_func_int8_t_s_s(
               (g_84 = (+(
                    ((safe_lshift_func_int16_t_s_u(
                         (l_660 = (-10)),
                         (((l_661 == 4U) ==
                           (((g_214 =
                                  ((+((-2) >
                                      ((safe_sub_func_int8_t_s_s(
                                           g_360,
                                           (safe_lshift_func_int8_t_s_u(
                                               (safe_lshift_func_int8_t_s_u(
                                                   g_54,
                                                   ((safe_lshift_func_uint16_t_u_u(
                                                        (safe_unary_minus_func_int32_t_s(
                                                            (safe_unary_minus_func_uint8_t_u(
                                                                (safe_lshift_func_int8_t_s_u(
                                                                    g_34,
                                                                    ((-5) >=
                                                                     (((g_306 = (safe_rshift_func_uint8_t_u_s(
                                                                            (g_126 >
                                                                             l_628),
                                                                            g_84))) |
                                                                       1U) &
                                                                      65535U)))))))),
                                                        g_172)) >= l_361))),
                                               6)))) != 3U))) != l_677)) ==
                             g_631) == g_33)) ^
                          0))) != g_34) >= g_172))),
               g_85)) |
           (-10));
      l_361 = 0;
      g_126 = (+(safe_sub_func_uint16_t_u_u(
          ((safe_sub_func_uint32_t_u_u(
               (((g_84 =
                      ((safe_sub_func_int32_t_s_s((l_660 | ((-3) != g_214)),
                                                  (g_33 | 0x02))) ||
                       (g_214 =
                            (0xD97ADD42 ||
                             (safe_lshift_func_int8_t_s_u(
                                 (((((l_660 <= (-2)) ==
                                     (safe_mod_func_uint8_t_u_u(
                                         (l_544 = (l_361 = (l_594 >= 0xD97C))),
                                         255U))) != 5) |
                                   0x23) < g_33),
                                 1)))))) ||
                 g_171) &
                l_689),
               g_522)) ||
           g_86),
          0U)));
    }
    l_361 = ((safe_unary_minus_func_uint8_t_u(((safe_lshift_func_uint8_t_u_u((l_544 = ((safe_sub_func_int16_t_s_s((-9), (((l_697 ^ (((!(!(((l_628 = ((((safe_add_func_int16_t_s_s((safe_lshift_func_int16_t_s_s((0x23 | 255U), 7)), 0U)) != (g_34 && ((0xC9A7E767 < g_170) & ((((safe_rshift_func_int16_t_s_u(((safe_rshift_func_uint16_t_u_s((g_545 = ((!((safe_lshift_func_int16_t_s_u((safe_rshift_func_uint8_t_u_s(l_594, 3)), l_32)) | l_544)) >= g_631)), 4)) & 0x58), 2)) >= 0xE9C4BE40) && g_83) != g_306)))) == g_170) | l_661)) & 251U) ^ g_83))) & l_362) > l_713)) < g_34) ^ 0U))) ^ l_594)), 6)) >= 0xF8F62C7F))) >= 0x0C);
    for (l_362 = (-3); (l_362 > 29); ++l_362) {
      DCEMarker3_();
      int16_t l_719 = 8;
      int32_t l_742 = 0x05E43C51;
      g_360 = (((+0xC5) !=
                (((g_123 = (safe_mod_func_uint16_t_u_u(
                       l_719,
                       (safe_sub_func_uint8_t_u_u(
                           (safe_mod_func_int32_t_s_s(
                               (g_306 !=
                                (((((((g_215 = (safe_mod_func_uint8_t_u_u(
                                           ((g_86 = 1) &
                                            (0x2E ||
                                             ((~(safe_mod_func_uint32_t_u_u(
                                                  (safe_rshift_func_uint8_t_u_s(
                                                      l_719, g_360)),
                                                  g_85))) ||
                                              (safe_mod_func_uint8_t_u_u(
                                                  l_661, l_719))))),
                                           l_719))) > l_719) <= 0x6367D79E) ^
                                    0x50BA) ||
                                   g_123) <= 0x9A8D835A) &
                                 0xC0)),
                               g_54)),
                           l_719))))) > (-6)) |
                 l_544)) >= 0xCB527FCE);
      g_360 =
          ((l_719 &&
            (((safe_add_func_int32_t_s_s(
                  (-9),
                  (safe_unary_minus_func_int16_t_s(
                      ((safe_lshift_func_int16_t_s_s(
                           (((-1) ^
                             ((safe_mod_func_int16_t_s_s((-10), 0x843F)) |
                              (safe_unary_minus_func_int8_t_s((
                                  (l_719 >= (((((l_742 = (((((l_719 || l_741) >
                                                             (-6)) <= g_49) |
                                                           g_522) |
                                                          l_719)) ^
                                                0xECC818A4) == 0x7DB3) <= 4U) ||
                                             6U)) > g_83))))) >= l_697),
                           5)) ||
                       0xF223))))) >= l_719) < l_719)) >= g_214);
      if (l_544) {
        DCEMarker6_();
        break;
      }
    }
    return l_743;
}
static uint32_t func_4(int32_t p_5, uint16_t p_6, int32_t p_7, int32_t p_8, uint32_t p_9)
{
    uint32_t l_578 = 0xC6D6B910;
    p_8 = (0U ^ (+p_9));
    g_360 = (g_33 == (p_9 < ((safe_mod_func_uint8_t_u_u((+((safe_add_func_uint16_t_u_u(0U, 0x7A24)) >= (safe_lshift_func_uint8_t_u_u(g_172, (p_9 <= (safe_sub_func_int32_t_s_s(((safe_unary_minus_func_int16_t_s((0xB9C1 == l_578))) <= (safe_mod_func_uint16_t_u_u((((((safe_sub_func_uint8_t_u_u((safe_unary_minus_func_uint8_t_u((safe_sub_func_int16_t_s_s(g_54, 0xAF74)))), 0x9C)) != 0xE7A00691) >= 0x802E) != 0x8174C16D) ^ 0), 0x001E))), g_545))))))), 0x09)) && 0x4A)));
    return l_578;
}
static int32_t func_10(uint32_t p_11, int32_t p_12)
{
    uint32_t l_551 = 0U;
    int32_t l_564 = (-9);
    int32_t l_565 = 0xD1EE99DB;
    int32_t l_566 = 0x97BEC5EA;
    l_566 = (safe_add_func_int16_t_s_s(((safe_lshift_func_uint16_t_u_u((0xBC != l_551), 5)) < (l_551 ^ (l_565 = (safe_sub_func_uint8_t_u_u((!0x7A69455F), (((-9) ^ (~l_551)) <= (g_126 = (g_214 < (g_34 = (safe_sub_func_int8_t_s_s((safe_sub_func_int8_t_s_s(((g_84 != (((((safe_add_func_int8_t_s_s((((safe_mod_func_int16_t_s_s((l_551 > p_11), 0xC01C)) < 0x379EFA2B) > l_551), g_215)) != g_86) < l_564) <= 0x31) != l_551)) || g_86), g_123)), 0x51))))))))))), 65535U));
    return p_12;
}
static uint16_t func_16(uint32_t p_17, int32_t p_18, int32_t p_19, uint32_t p_20, int8_t p_21)
{
    return p_18;
}
static uint16_t func_24(uint16_t p_25, uint8_t p_26, uint32_t p_27, int32_t p_28, uint8_t p_29)
{
    int16_t l_363 = 6;
    int32_t l_385 = (-2);
    int32_t l_388 = 0x1EFFA761;
    int32_t l_389 = 0x55EECBC7;
    int32_t l_390 = 0x165DB6DB;
    int32_t l_398 = 0xFECBAB64;
    uint16_t l_473 = 0xBBEB;
    int8_t l_474 = 0xDD;
    uint16_t l_475 = 0xA0A4;
    uint8_t l_491 = 0U;
    uint16_t l_492 = 1U;
    int32_t l_542 = (-3);
lbl_395:
    g_360 = l_363;
    if ((l_363 || (0x6E | (l_363 | (g_360 ^ (g_170 < l_363)))))) {
      DCEMarker7_();
      int32_t l_384 = 1;
      int32_t l_386 = (-10);
      uint32_t l_387 = 0x0D89AA81;
      int32_t l_428 = 3;
      uint32_t l_435 = 1U;
      uint32_t l_446 = 4294967289U;
      uint8_t l_524 = 0xBC;
        l_390 = (l_389 = (l_388 = ((0x46 | ((p_26 = (((g_85 && (safe_mod_func_int32_t_s_s((safe_rshift_func_int16_t_s_u((safe_sub_func_uint8_t_u_u((l_363 < (p_25 = (0xEBB756B0 | (p_27 > (safe_sub_func_int32_t_s_s((p_25 & (safe_rshift_func_int16_t_s_s((safe_add_func_int8_t_s_s((!(((g_34 <= (safe_lshift_func_uint8_t_u_u((((g_215 = ((((safe_mod_func_uint16_t_u_u((g_170 = ((0 && ((p_28 = ((((((l_386 = (+((l_385 = (safe_sub_func_uint8_t_u_u(((((((g_360 != g_215) >= 0U) & l_384) ^ p_25) == 0xAF) <= l_384), l_363))) & p_26))) ^ l_387) != 0x3331) >= l_363) && g_2) & l_363)) >= l_387)) != p_29)), l_387)) == 0xEFC80D1E) ^ g_171) ^ l_387)) ^ (-4)) | l_384), 3))) != g_84) == p_26)), l_384)), 5))), l_384)))))), l_384)), g_123)), 0x37194E90))) ^ 1) != g_306)) != g_171)) ^ g_54)));
        for (g_126 = 2; (g_126 == (-11)); --g_126) {
          DCEMarker10_();
          int32_t l_427 = (-1);
          for (l_388 = (-18); (l_388 != 10); l_388++) {
            DCEMarker14_();
            uint32_t l_429 = 0x84E49481;
            int32_t l_445 = 0x830CA0FB;
            g_360 = p_29;
            if (g_306) {
              DCEMarker15_();
              goto lbl_395;
            }
            for (g_306 = 19; (g_306 == 45);
                 g_306 = safe_add_func_uint8_t_u_u(g_306, 1)) {
              DCEMarker16_();
              int32_t l_444 = 0;
              int32_t l_451 = (-3);
              if (l_398) {
                DCEMarker17_();
                break;
              }
              for (g_49 = (-17); (g_49 > 59);
                   g_49 = safe_add_func_uint16_t_u_u(g_49, 9)) {
                DCEMarker18_();
                p_28 = 0x42F424CE;
                g_360 =
                    (g_33 ^
                     ((safe_sub_func_uint8_t_u_u(
                          l_384,
                          ((((safe_lshift_func_uint8_t_u_u((g_214 = g_33),
                                                           (p_29 = 0x42))) ==
                             (g_85 ||
                              (safe_rshift_func_uint8_t_u_s(
                                  ((safe_rshift_func_int8_t_s_s(
                                       (0xD60C2995 ^
                                        ((p_27 ==
                                          (p_28 =
                                               (((safe_mod_func_uint8_t_u_u(
                                                     (safe_unary_minus_func_int8_t_s(
                                                         p_25)),
                                                     5)) &&
                                                 9) &&
                                                l_389))) ^
                                         g_215)),
                                       g_49)) ^
                                   p_25),
                                  g_215)))) < (-8)) |
                           1))) > p_27));
                g_360 =
                    (p_25 <=
                     (safe_add_func_uint32_t_u_u(
                         (255U == (safe_unary_minus_func_uint16_t_u(g_85))),
                         ((safe_add_func_uint32_t_u_u(
                              (((l_389 = (safe_unary_minus_func_uint16_t_u((
                                     ((((safe_rshift_func_uint8_t_u_s(
                                            (safe_add_func_uint32_t_u_u(
                                                ((((((safe_sub_func_int16_t_s_s(
                                                         (safe_sub_func_uint16_t_u_u(
                                                             g_360,
                                                             (l_429 = (+(
                                                                  0xBAA4C629 <=
                                                                  (l_428 =
                                                                       (l_386 =
                                                                            l_427))))))),
                                                         (safe_mod_func_uint32_t_u_u(
                                                             ((l_445 = (safe_mod_func_uint8_t_u_u(
                                                                   ((+(l_435 &&
                                                                       (safe_rshift_func_uint16_t_u_u(
                                                                           p_28,
                                                                           (safe_sub_func_int8_t_s_s(
                                                                               ((safe_lshift_func_uint8_t_u_s(
                                                                                    ((safe_sub_func_int16_t_s_s(
                                                                                         p_26,
                                                                                         l_444)) !=
                                                                                     p_29),
                                                                                    0)) &&
                                                                                l_427),
                                                                               p_29)))))) |
                                                                    l_445),
                                                                   l_446))) >=
                                                              0x12CA),
                                                             (-1))))) |
                                                     l_385) < l_444) &&
                                                   g_123) &
                                                  p_26) >= g_215),
                                                1U)),
                                            2)) != 0x3C09) &&
                                       p_26) < p_29) < g_86)))) > p_28) <=
                               (-5)),
                              l_427)) &&
                          p_29))));
                l_445 = (g_126 |
                         (255U >
                          (g_214 = ((((g_85 && 0x425D56D3) ==
                                      (((g_360 = l_444) || g_33) <=
                                       ((((safe_add_func_int8_t_s_s(
                                              ((l_451 = g_83) >=
                                               (l_427 = ((7U || 3) ^ g_214))),
                                              p_28)) == p_29) &
                                         g_171) == 2))) != 0x643CAA11) |
                                    65532U))));
              }
              g_360 = g_33;
            }
          }
          g_360 = (l_386 = (l_390 = 0));
        }
        if ((safe_lshift_func_uint8_t_u_s(
                (safe_mod_func_int8_t_s_s(
                    g_172,
                    (l_389 = (safe_unary_minus_func_int32_t_s(
                         (safe_add_func_uint8_t_u_u(
                             (safe_sub_func_uint32_t_u_u(
                                 (0x3A &&
                                  (safe_lshift_func_int16_t_s_u(
                                      (0U >=
                                       (safe_add_func_int8_t_s_s(
                                           (safe_mod_func_int8_t_s_s(
                                               (((safe_sub_func_uint32_t_u_u(
                                                     g_214,
                                                     (!(l_390 =
                                                            (safe_unary_minus_func_int32_t_s(
                                                                (-10))))))) ||
                                                 (safe_lshift_func_uint8_t_u_s(
                                                     (0x0DD65361 &
                                                      ((p_26 = g_2) && p_29)),
                                                     (((l_473 < l_474) &
                                                       g_85) &&
                                                      0x4A36ACEA)))) ||
                                                65535U),
                                               l_386)),
                                           0))),
                                      g_170))),
                                 g_170)),
                             l_475))))))),
                6))) {
          DCEMarker11_();
          return p_26;
        } else {
          DCEMarker12_();
          uint8_t l_490 = 253U;
          int32_t l_509 = 0x2D6179AE;
          int32_t l_523 = 0xBBA16F17;
          g_126 = (safe_rshift_func_int8_t_s_u(
              ((((0 | 0x76E6) == g_33) ||
                (safe_sub_func_int32_t_s_s(
                    ((g_214 =
                          ((safe_add_func_int8_t_s_s(
                               (safe_mod_func_int16_t_s_s(
                                   (safe_sub_func_uint8_t_u_u(
                                       (l_386 = (safe_lshift_func_int16_t_s_s(
                                            l_384, 0))),
                                       ((g_170 < (-1)) |
                                        ((((g_360 = 0x3EA50121) !=
                                           ((((g_171 >
                                               ((safe_lshift_func_uint16_t_u_u(
                                                    0U, l_446)) < l_490)) >
                                              l_491) != l_387) == p_28)) ==
                                          l_475) == g_49)))),
                                   p_27)),
                               g_215)) <= 0x8BD9AB2F)) ||
                     g_83),
                    g_33))) == g_171),
              l_492));
          g_360 = (safe_mod_func_int32_t_s_s(
              (+((l_523 =
                      ((safe_sub_func_uint16_t_u_u(
                           (p_25 = (safe_rshift_func_int8_t_s_s(
                                (safe_rshift_func_uint8_t_u_s(g_34, 0)),
                                (safe_unary_minus_func_int16_t_s((safe_add_func_int32_t_s_s(
                                    (safe_add_func_int16_t_s_s(
                                        (g_215 ^
                                         ((safe_sub_func_uint32_t_u_u(
                                              (l_509 = g_171),
                                              ((safe_lshift_func_int16_t_s_s(
                                                   (((l_490 <=
                                                      (safe_rshift_func_uint8_t_u_s(
                                                          ((((safe_add_func_int8_t_s_s(
                                                                 (g_214 |
                                                                  (safe_add_func_int8_t_s_s(
                                                                      p_26,
                                                                      (((safe_lshift_func_uint16_t_u_s(
                                                                            (((g_86 =
                                                                                   p_26) ^
                                                                              ((p_25 >=
                                                                                (((p_27 >=
                                                                                   0xBE39) >
                                                                                  1U) ||
                                                                                 p_28)) !=
                                                                               g_2)) &&
                                                                             p_26),
                                                                            0)) |
                                                                        g_170) <
                                                                       l_388)))),
                                                                 0x58)) <= 7) <=
                                                            g_33) &&
                                                           g_522),
                                                          l_363))) ||
                                                     g_54) |
                                                    g_215),
                                                   l_490)) |
                                               p_25))) < 247U)),
                                        65535U)),
                                    l_490))))))),
                           0x674A)) == 0x0EAAB445)) ||
                 1U)),
              l_524));
        }
        DCEMarker13_();
    } else {
      DCEMarker8_();
      int32_t l_525 = (-1);
      int32_t l_529 = 0x199A4D6B;
      g_522 = 0;
      g_522 = g_360;
      l_542 =
          (g_126 =
               (((l_525 <
                  (l_525 |
                   (((l_529 = (safe_sub_func_uint8_t_u_u((+p_28), 0x49))) &
                     g_170) ^
                    ((safe_add_func_uint8_t_u_u(
                         ((l_385 =
                               ((g_360 &&
                                 (safe_rshift_func_int8_t_s_u(
                                     1,
                                     (safe_lshift_func_int16_t_s_u(
                                         (((safe_add_func_uint32_t_u_u(
                                               (l_390 = g_306),
                                               (g_54 =
                                                    ((safe_rshift_func_int16_t_s_u(
                                                         (l_389 =
                                                              (((safe_sub_func_uint32_t_u_u(
                                                                    (0x5A65C302 <=
                                                                     g_33),
                                                                    l_525)) >=
                                                                g_2) ||
                                                               p_28)),
                                                         0)) |
                                                     l_491)))) ^
                                           p_27) == p_29),
                                         13))))) >= g_34)) &&
                          2U),
                         g_123)) != g_34)))) != p_29) &&
                (-8)));
    }
    DCEMarker9_();
    return p_25;
}
static uint8_t func_35(uint16_t p_36, uint32_t p_37, uint32_t p_38, uint32_t p_39)
{
    return g_360;
}
static uint16_t func_40(int32_t p_41, uint8_t p_42)
{
    uint32_t l_53 = 8U;
    int32_t l_66 = 0xBE72F236;
    int8_t l_71 = 0x12;
    int32_t l_82 = 1;
    int32_t l_91 = (-3);
    int16_t l_168 = 0xDD2E;
    int32_t l_169 = 0x3AB66917;
    uint8_t l_198 = 1U;
    int32_t l_304 = 0x480F0B60;
    int16_t l_354 = 1;
    int32_t l_355 = 8;
    g_49 = p_41;
    if ((+(p_41 == 5))) {
      DCEMarker19_();
      uint32_t l_87 = 0U;
      int32_t l_90 = 0;
      g_123 =
          (p_41 =
               (func_51((l_53 = (-1))) ==
                (func_56(
                     ((safe_sub_func_uint16_t_u_u(
                          (l_90 = func_63(
                               ((((l_66 > 0xBD28A218) >=
                                  ((1U !=
                                    ((g_86 = (safe_rshift_func_int8_t_s_s(
                                          (((((((g_85 = (safe_add_func_int8_t_s_s(
                                                     l_71,
                                                     ((g_84 =
                                                           ((((((safe_sub_func_uint32_t_u_u(
                                                                    p_42, 1U)) <
                                                                (safe_add_func_uint32_t_u_u(
                                                                    (((safe_rshift_func_uint16_t_u_u(
                                                                          (((safe_add_func_int32_t_s_s(
                                                                                (g_83 =
                                                                                     (l_82 =
                                                                                          ((+(safe_unary_minus_func_int16_t_s(
                                                                                               0))) >
                                                                                           0xE206))),
                                                                                0U)) ^
                                                                            (-3)) &
                                                                           p_41),
                                                                          8)) |
                                                                      g_2) &&
                                                                     4294967295U),
                                                                    p_42))) >
                                                               0x248F) ==
                                                              g_2) ||
                                                             g_83) <=
                                                            0xD51DC99B)) &
                                                      p_41)))) > g_2) > g_49) !=
                                              (-1)) < g_2) >= 0U) &&
                                           0x58),
                                          4))) &&
                                     0xEDF2CFEA)) != p_42)) < g_49) &&
                                p_42),
                               l_87)),
                          p_41)) &&
                      0x501D2D5F),
                     l_91, p_42, l_91) != p_41)));
    } else {
      DCEMarker20_();
      int8_t l_139 = (-1);
      int32_t l_140 = 8;
      int32_t l_141 = 3;
      l_66 = ((((g_85 && 0x19) < p_42) & 0) < p_41);
      l_141 =
          (g_126 =
               ((-1) <
                (l_66 = (safe_sub_func_uint32_t_u_u(
                     g_126,
                     (l_82 =
                          (((((((l_91 =
                                     (((safe_rshift_func_uint16_t_u_s(
                                           (((safe_sub_func_int16_t_s_s(
                                                 g_123, 0x947F)) ||
                                             (~(p_41 | (+g_54)))) &
                                            0x27A0C98A),
                                           ((safe_lshift_func_int16_t_s_u(
                                                (l_140 =
                                                     (((((safe_mod_func_uint8_t_u_u(
                                                             ((0x8D97F969 |
                                                               ((safe_add_func_uint8_t_u_u(
                                                                    p_42,
                                                                    g_54)) >
                                                                (-1))) >= g_85),
                                                             p_41)) <= p_42) &
                                                        0x43FB) < p_41) |
                                                      l_139)),
                                                1)) < l_139))) <= 4) > p_41)) &
                                p_41) &&
                               g_83) &
                              0x2DAC) ^
                             3) &&
                            p_42) > g_126)))))));
    }
    g_172 = (safe_rshift_func_int8_t_s_s((g_171 = ((safe_add_func_int8_t_s_s((g_84 = (-1)), g_85)) > ((((safe_mod_func_int16_t_s_s((1U != (safe_mod_func_int16_t_s_s((safe_rshift_func_uint16_t_u_u((safe_sub_func_uint32_t_u_u(l_71, (safe_add_func_int32_t_s_s((safe_mod_func_int16_t_s_s((~0xC2), 65529U)), (g_170 = (safe_sub_func_int8_t_s_s(((g_126 = (l_91 <= ((((l_169 = (safe_add_func_int16_t_s_s((((safe_rshift_func_int8_t_s_s((safe_unary_minus_func_int16_t_s((l_66 = (l_82 = (((((safe_sub_func_int32_t_s_s(((0x56C2 || 2) != p_42), p_41)) ^ g_126) | g_85) == p_42) != (-1)))))), 0)) || 0xD7) < l_168), 0x8DEF))) >= l_71) == l_53) < g_85))) != l_53), 0xA2))))))), 0)), 6))), p_42)) || l_91) && p_41) != 0x9A39686C))), 6));
    for (l_91 = 0; (l_91 >= 0); l_91 = safe_add_func_uint32_t_u_u(l_91, 8)) {
      DCEMarker22_();
      int16_t l_179 = 0x16FF;
      int32_t l_197 = 0xA55BADF4;
      int32_t l_228 = 0xED988206;
      uint16_t l_336 = 0x255E;
      int8_t l_353 = 3;
      for (p_42 = 21; (p_42 <= 57); ++p_42) {
        DCEMarker23_();
        uint32_t l_196 = 0x2EAEB8C4;
        int32_t l_241 = 0xDD45D5CC;
        int32_t l_319 = (-4);
        if (((((g_171 |
                ((safe_sub_func_int32_t_s_s(
                     (l_179 |
                      (safe_add_func_uint8_t_u_u(
                          (safe_rshift_func_int8_t_s_u(
                              ((0x55 ^
                                (l_169 = (safe_sub_func_int8_t_s_s(
                                     (safe_add_func_int16_t_s_s(0x754C,
                                                                0x22BE)),
                                     (safe_add_func_int32_t_s_s(
                                         (g_84 !=
                                          (safe_sub_func_int16_t_s_s(
                                              (((safe_add_func_int16_t_s_s(
                                                    (-6), g_123)) >=
                                                (((safe_lshift_func_int8_t_s_s(
                                                      (l_196 = l_82), l_71)) <
                                                  g_83) |
                                                 0x76)) |
                                               l_179),
                                              0x3E8D))),
                                         p_41)))))) < p_42),
                              g_84)),
                          g_172))),
                     l_82)) ^
                 p_42)) != 0x307A) &
              p_42) == 0xF1)) {
          DCEMarker25_();
          int32_t l_216 = 7;
          uint16_t l_227 = 65531U;
          int32_t l_275 = 0xE6F1A905;
          p_41 = p_41;
          if (l_197) {
            DCEMarker28_();
            uint32_t l_203 = 4294967288U;
            int32_t l_205 = 2;
            int32_t l_217 = 0xA718D19A;
            p_41 = (l_198 & 255U);
            l_217 = (safe_mod_func_uint8_t_u_u(
                (((g_84 = (safe_sub_func_uint16_t_u_u(l_203, 0xF97A))) ==
                  g_85) != ((+(l_205 = p_42)) >= p_41)),
                ((safe_add_func_uint16_t_u_u(
                     (((((((safe_mod_func_uint16_t_u_u(
                               (((safe_lshift_func_uint8_t_u_s(
                                     ((0x7F268E3A > l_196) &&
                                      (((safe_mod_func_uint32_t_u_u(
                                            (g_172 =
                                                 ((l_179 &&
                                                   ((g_215 = (g_214 = (-8))) |
                                                    1)) > p_42)),
                                            0x9E441701)) <= p_42) &
                                       l_216)),
                                     g_126)) > p_41) == g_85),
                               p_41)) == l_203) ||
                          5U) != g_2) == 1) != g_123) ||
                      g_215),
                     p_41)) ^
                 l_71)));
          } else {
            DCEMarker29_();
            uint32_t l_222 = 0U;
            uint8_t l_248 = 0x96;
            g_126 = (((g_54 == (((-5) && l_216) <
                                (safe_sub_func_uint8_t_u_u(
                                    (65535U & g_86),
                                    (0x741D2212 > (safe_add_func_int32_t_s_s(
                                                      ((l_222 & p_41) > 0x4D),
                                                      0x728182F1))))))) ==
                      p_41) <= p_42);
            l_216 =
                (((safe_rshift_func_uint16_t_u_s(
                      (l_228 = ((safe_add_func_int8_t_s_s(l_227, 0xC9)) <
                                (l_197 = l_197))),
                      3)) ==
                  ((((-1) && g_171) <=
                    (safe_rshift_func_uint16_t_u_u(
                        0x49DF,
                        ((safe_lshift_func_int8_t_s_s(
                             (safe_rshift_func_uint8_t_u_s(
                                 ((safe_mod_func_uint16_t_u_u(
                                      (safe_add_func_int8_t_s_s(
                                          (safe_add_func_int16_t_s_s(
                                              (((((l_241 = (g_49 != l_179)) ||
                                                  ((safe_sub_func_int16_t_s_s(
                                                       (((safe_add_func_int8_t_s_s(
                                                             (safe_mod_func_int16_t_s_s(
                                                                 p_42, 0xA6AA)),
                                                             l_196)) &&
                                                         0xFB) &
                                                        l_179),
                                                       l_248)) |
                                                   0xB6)) != l_66) == 0x6B11) <
                                               0x5D),
                                              l_179)),
                                          p_42)),
                                      l_227)) ^
                                  0x38),
                                 p_41)),
                             0)) &&
                         0xD099)))) >= 0x23)) |
                 l_179);
            for (l_168 = 0; (l_168 != (-24));
                 l_168 = safe_sub_func_int32_t_s_s(l_168, 8)) {
              DCEMarker30_();
              p_41 = (safe_lshift_func_uint8_t_u_u(
                  ((safe_sub_func_uint8_t_u_u(g_86, (g_123 = g_123))) <= l_179),
                  3));
              p_41 = p_42;
              g_126 = (safe_lshift_func_int16_t_s_u(
                  (safe_add_func_int16_t_s_s(g_214, l_248)), 2));
            }
            p_41 = ((g_49 = l_227) |
                    ((safe_add_func_uint8_t_u_u(((l_53 >= 0x8FEB) >= l_248),
                                                (0U != (l_197 || l_216)))) |
                     (l_241 = 0x7E2D)));
          }
          l_275 = (safe_sub_func_uint16_t_u_u(
              (safe_sub_func_uint8_t_u_u(
                  g_84,
                  ((l_179 >=
                    ((safe_add_func_int8_t_s_s(p_42, l_168)) <=
                     (((0x76B8 ^
                        (((safe_rshift_func_int16_t_s_s(
                              (safe_lshift_func_uint16_t_u_s(
                                  ((l_216 = g_170) ^
                                   (l_227 >
                                    (safe_add_func_uint8_t_u_u(
                                        (0xA5 |
                                         ((l_66 =
                                               (g_171 =
                                                    (safe_lshift_func_int16_t_s_u(
                                                        p_42, l_227)))) >=
                                          l_227)),
                                        1)))),
                                  l_227)),
                              6)) > 0x8B93ECFD) &&
                         g_54)) ^
                       l_197) &&
                      p_41))) == 1))),
              p_41));
          l_82 = p_42;
        } else {
          DCEMarker26_();
          p_41 = ((g_83 >= (p_41 || (l_66 = 6))) ==
                  ((~(l_82 = 8U)) & ((l_241 = (safe_rshift_func_int8_t_s_s(
                                          (g_84 = (-4)), 6))) < p_41)));
        }
        for (g_126 = 8; (g_126 == (-2));
             g_126 = safe_sub_func_uint8_t_u_u(g_126, 4)) {
          DCEMarker27_();
          int32_t l_300 = (-6);
          int32_t l_303 = 1;
          uint32_t l_305 = 0U;
          int16_t l_318 = 0xE831;
          l_304 =
              ((g_215 || ((safe_rshift_func_int16_t_s_s(g_85, 8)) || l_196)) >
               (l_169 =
                    ((l_241 =
                          ((safe_mod_func_int8_t_s_s(
                               9,
                               (safe_mod_func_uint8_t_u_u(
                                   (p_42 ==
                                    ((p_41 &&
                                      ((((g_84 =
                                              (((safe_rshift_func_uint16_t_u_s(
                                                    (((safe_mod_func_int16_t_s_s(
                                                          (safe_lshift_func_uint16_t_u_u(
                                                              ((((+0) >=
                                                                 (safe_add_func_int32_t_s_s(
                                                                     (((((safe_mod_func_int16_t_s_s(
                                                                             ((safe_sub_func_int8_t_s_s(
                                                                                  (((g_123 =
                                                                                         (l_300 =
                                                                                              l_179)) |
                                                                                    ((((((safe_add_func_int32_t_s_s(
                                                                                             (l_303 !=
                                                                                              g_83),
                                                                                             g_85)) >=
                                                                                         l_303) ^
                                                                                        p_41) ||
                                                                                       l_304) <=
                                                                                      p_41) &
                                                                                     g_170)) &&
                                                                                   g_123),
                                                                                  l_303)) &
                                                                              p_41),
                                                                             g_83)) &&
                                                                         0xCC53) |
                                                                        p_41) &
                                                                       l_169) ==
                                                                      l_241),
                                                                     p_41))) ^
                                                                l_305) ^
                                                               0xCD),
                                                              2)),
                                                          (-1))) &&
                                                      g_126) != g_86),
                                                    10)) >= p_41) == g_171)) <=
                                         l_303) <= 1) &
                                       l_66)) <= p_42)),
                                   0xDD)))) == l_305)) &
                     g_172)));
          g_306 = (p_41 || 9);
          p_41 = (safe_rshift_func_uint16_t_u_u(
              ((safe_sub_func_int32_t_s_s(l_169, p_41)) !=
               (safe_sub_func_int16_t_s_s(
                   ((g_86 || ((l_241 = g_171) <= p_41)) |
                    (safe_sub_func_int8_t_s_s(
                        ((l_319 =
                              ((l_304 = (!(((safe_mod_func_int32_t_s_s(
                                                l_168, l_318)) > l_198) ==
                                           (((l_303 = l_169) > 0x3E141900) !=
                                            l_196)))) <= g_85)) |
                         0x82),
                        g_215))),
                   (-1)))),
              p_41));
        }
        g_126 = 0;
      }
      l_228 = g_123;
      for (g_214 = 25; (g_214 > 8);
           g_214 = safe_sub_func_int32_t_s_s(g_214, 5)) {
        DCEMarker24_();
        uint8_t l_328 = 0xDC;
        int32_t l_331 = 0x1A96DB85;
        int32_t l_356 = 0x5DCA2D12;
        int32_t l_357 = (-7);
        p_41 = g_83;
        p_41 = (g_126 = (safe_rshift_func_uint8_t_u_s(
                    (0U == g_83),
                    (safe_sub_func_int8_t_s_s(
                        ((253U != ((g_215 == (safe_add_func_uint16_t_u_u(
                                                 (l_328 || 7U),
                                                 (((safe_mod_func_uint8_t_u_u(
                                                       g_172, p_41)) ^
                                                   ((l_331 & 0xD332) | g_83)) &
                                                  g_85)))) == (-1))) &
                         p_42),
                        p_42)))));
        l_357 =
            (((((((((safe_sub_func_int16_t_s_s(
                        (safe_mod_func_uint8_t_u_u(
                            l_336,
                            ((safe_add_func_uint32_t_u_u(
                                 (l_82 =
                                      ((g_214 >=
                                        (l_356 =
                                             (((safe_rshift_func_uint8_t_u_s(
                                                   (safe_rshift_func_uint16_t_u_s(
                                                       (2 ^
                                                        (0xF2 ==
                                                         (l_304 =
                                                              (1U !=
                                                               (((safe_mod_func_int32_t_s_s(
                                                                     (safe_rshift_func_int16_t_s_u(
                                                                         (safe_rshift_func_uint8_t_u_s(
                                                                             g_214,
                                                                             0)),
                                                                         (l_331 = (safe_lshift_func_uint16_t_u_s(
                                                                              (safe_add_func_int16_t_s_s(
                                                                                  l_353,
                                                                                  (g_215 ^
                                                                                   0xF6))),
                                                                              15))))),
                                                                     (-10))) &
                                                                 g_85) >
                                                                l_354))))),
                                                       7)),
                                                   g_126)) &&
                                               p_42) &
                                              l_355))) |
                                       l_179)),
                                 0xEDCCFC09)) &
                             g_49))),
                        6U)) &
                    g_214) < g_306) <= l_91) ^
                 1) < 0xE3) &&
               l_179) ^
              4U) >= p_42);
        l_356 = (safe_mod_func_uint32_t_u_u(0U, 4294967290U));
      }
      return l_66;
    }
    DCEMarker21_();
    return l_355;
}
static int16_t func_51(int8_t p_52)
{
    int32_t l_55 = 0;
    g_54 = p_52;
    l_55 = 0x1FC53136;
    return p_52;
}
static int8_t func_56(uint16_t p_57, int8_t p_58, uint8_t p_59, int8_t p_60)
{
    uint16_t l_120 = 0xB992;
    int32_t l_121 = 0xD7FF4CBE;
    int32_t l_122 = 0;
    l_122 = ((safe_sub_func_int8_t_s_s((safe_sub_func_uint32_t_u_u((safe_lshift_func_uint8_t_u_s((safe_rshift_func_int16_t_s_s(g_2, (((safe_lshift_func_int16_t_s_s((safe_lshift_func_uint16_t_u_s(p_60, 4)), 13)) != 0x47) <= g_83))), 1)), (safe_add_func_uint16_t_u_u(((safe_mod_func_uint8_t_u_u(((safe_sub_func_int16_t_s_s(0xC0AC, (safe_mod_func_uint8_t_u_u((8U >= (safe_sub_func_int16_t_s_s((safe_rshift_func_int16_t_s_s((l_121 = ((0U || (((((((safe_lshift_func_uint16_t_u_s(g_85, 7)) != (l_120 >= l_120)) && 0x0DA4) & p_57) <= g_49) && p_58) || p_59)) == l_120)), 0)), (-1)))), g_84)))) ^ p_60), p_60)) > l_120), p_60)))), 0)) >= 0x1C7C);
    return l_120;
}
static uint16_t func_63(int8_t p_64, int8_t p_65)
{
    int32_t l_88 = 0xF089E30C;
    int32_t l_89 = (-1);
    l_89 = l_88;
    return g_2;
}
int main (void)
{
    int print_hash_value = 0;
    platform_main_begin();
    crc32_gentab();
    func_1();
    transparent_crc(g_2, "g_2", print_hash_value);
    transparent_crc(g_3, "g_3", print_hash_value);
    transparent_crc(g_33, "g_33", print_hash_value);
    transparent_crc(g_34, "g_34", print_hash_value);
    transparent_crc(g_49, "g_49", print_hash_value);
    transparent_crc(g_54, "g_54", print_hash_value);
    transparent_crc(g_83, "g_83", print_hash_value);
    transparent_crc(g_84, "g_84", print_hash_value);
    transparent_crc(g_85, "g_85", print_hash_value);
    transparent_crc(g_86, "g_86", print_hash_value);
    transparent_crc(g_123, "g_123", print_hash_value);
    transparent_crc(g_126, "g_126", print_hash_value);
    transparent_crc(g_170, "g_170", print_hash_value);
    transparent_crc(g_171, "g_171", print_hash_value);
    transparent_crc(g_172, "g_172", print_hash_value);
    transparent_crc(g_214, "g_214", print_hash_value);
    transparent_crc(g_215, "g_215", print_hash_value);
    transparent_crc(g_306, "g_306", print_hash_value);
    transparent_crc(g_360, "g_360", print_hash_value);
    transparent_crc(g_522, "g_522", print_hash_value);
    transparent_crc(g_543, "g_543", print_hash_value);
    transparent_crc(g_545, "g_545", print_hash_value);
    transparent_crc(g_631, "g_631", print_hash_value);
    platform_main_end(crc32_context ^ 0xFFFFFFFFUL, print_hash_value);
    return 0;
}
